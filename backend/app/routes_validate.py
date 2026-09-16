"""
검증 전용 API — 이미 작업이 끝난 자막을 후처리 없이 검증만 한다.

테스트 파이프라인(routes_test)이 "단계별로 무엇이 일어나는가"를 보여준다면
여기는 "이 자막의 어디가 규격에 어긋나는가"를 자막 단위로 모아서 돌려준다.
검증 함수 실행 자체는 engine/runner.py 를 공유하므로 결과가 갈리지 않는다.
"""
import logging

import srt
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.engine import rules
from app.engine.runner import (
    run_validation, timecode, validation_params_for, weighted_length,
)
from app.models import Mapping, TechItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/validate", tags=["validate"])


class ValidateRequest(BaseModel):
    srt_text: str
    broadcaster_id: str
    items: list[str] = []          # 비우면 방송사 기본 검증 항목 전체
    params_override: dict = {}


def _default_validation_items(db: Session, broadcaster_id: str):
    """
    방송사 파이프라인의 검증 항목을 실행 순서대로.

    같은 함수 + 같은 파라미터가 1차·2차에 중복 등록돼 있는데, 검증 탭은 후처리를
    돌리지 않아 두 번 다 결과가 같다. 화면에 같은 오류가 두 줄로 나오는 걸 막으려고
    먼저 나온 것만 남긴다 (사용자가 직접 고르면 그대로 존중한다).
    """
    rows = (
        db.query(Mapping, TechItem)
        .join(TechItem, TechItem.id == Mapping.item_id)
        .filter(Mapping.broadcaster_id == broadcaster_id, TechItem.type == "validation")
        .order_by(Mapping.sort_order)
        .all()
    )
    items, seen, duplicates = [], set(), 0
    for _, t in rows:
        key = (t.function_name, tuple(sorted((t.params or {}).items())))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        items.append(t)
    return items, duplicates


@router.get("/items/{broadcaster_id}")
def default_items(broadcaster_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """방송사 기본 검증 항목 (중복 제거된 실행 순서)."""
    items, duplicates = _default_validation_items(db, broadcaster_id)
    return {
        "broadcaster_id": broadcaster_id,
        "validation_params": validation_params_for(db, broadcaster_id),
        "deduped_count": duplicates,
        "items": [
            {
                "id": t.id, "name": t.name, "function_name": t.function_name,
                "func_type": t.func_type, "stage": t.stage, "scope": t.scope,
                "desc": t.desc, "params": t.params or {},
            }
            for t in items
        ],
    }


@router.post("/run")
def run_validation_only(body: ValidateRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    try:
        subs = list(srt.parse(body.srt_text))
    except Exception as e:
        return {"error": f"SRT 파싱 실패: {e}"}
    if not subs:
        return {"error": "SRT 파싱 실패: 유효한 자막이 없습니다."}

    vp = validation_params_for(db, body.broadcaster_id)

    item_ids = body.items
    if not item_ids:
        item_ids = [t.id for t in _default_validation_items(db, body.broadcaster_id)[0]]

    rows = {t.id: t for t in db.query(TechItem).filter(TechItem.id.in_(item_ids)).all()} if item_ids else {}

    # 자막 단위 결과 뼈대 — 오류가 없어도 전부 내려서 화면에서 "전체 보기"가 가능하게 한다.
    by_index = {}
    entries = []
    for s in subs:
        entry = {
            "index": s.index,
            "timecode": timecode(s),
            "text": s.content,
            "lines": [
                {"text": line, "length": round(weighted_length(line, vp), 1)}
                for line in s.content.split("\n")
            ],
            "duration_sec": round((s.end - s.start).total_seconds(), 3),
            "errors": [],
        }
        entries.append(entry)
        by_index.setdefault(s.index, entry)

    rule_results = []
    unmatched = []
    total_errors = 0

    for item_id in item_ids:
        item = rows.get(item_id)
        if item is None:
            rule_results.append({"id": item_id, "name": "알 수 없는 항목", "function_name": "",
                                 "status": "error", "error_count": 0, "params_used": {},
                                 "info": "항목을 찾을 수 없습니다."})
            continue
        if item.type != "validation":
            rule_results.append({"id": item.id, "name": item.name, "function_name": item.function_name,
                                 "status": "skip", "error_count": 0, "params_used": {},
                                 "info": "검증 항목이 아니라 건너뜀 (검증 탭은 후처리를 실행하지 않습니다)"})
            continue

        params = dict(item.params or {})
        if item_id in body.params_override:
            params.update(body.params_override[item_id])

        fn = getattr(rules, item.function_name, None)
        base = {"id": item.id, "name": item.name, "function_name": item.function_name,
                "stage": item.stage, "scope": item.scope, "desc": item.desc,
                "params_used": params}

        if fn is None:
            rule_results.append({**base, "status": "skip", "error_count": 0,
                                 "info": f"미구현 함수: {item.function_name}()"})
            continue

        try:
            errors = run_validation(item, fn, subs, params, vp)
        except Exception as e:
            logger.exception("validation step failed: %s", item.function_name)
            rule_results.append({**base, "status": "error", "error_count": 0,
                                 "info": f"실행 오류: {e}"})
            continue

        for err in errors:
            payload = {
                "rule_id": item.id,
                "rule_name": item.name,
                "function_name": item.function_name,
                "message": err.get("message", ""),
                "type": err.get("type", item.function_name),
                "line": err.get("line"),
                "char_count": err.get("char_count"),
                "limit": err.get("limit"),
            }
            entry = by_index.get(err.get("index"))
            if entry is not None:
                entry["errors"].append(payload)
            else:
                unmatched.append({**payload, "index": err.get("index")})

        total_errors += len(errors)
        rule_results.append({
            **base,
            "status": "fail" if errors else "pass",
            "error_count": len(errors),
            "info": (f"{len(errors)}건 재작업" if errors else "오류 없음"),
        })

    error_entry_count = sum(1 for e in entries if e["errors"])
    ran = [r for r in rule_results if r["status"] in ("pass", "fail")]

    return {
        "broadcaster_id": body.broadcaster_id,
        "validation_params": vp,
        "srt_entry_count": len(entries),
        "rule_count": len(rule_results),
        "ran_count": len(ran),
        "error_count": total_errors,
        "error_entry_count": error_entry_count,
        "passed": total_errors == 0,
        "rules": rule_results,
        "entries": entries,
        "unmatched_errors": unmatched,
    }
