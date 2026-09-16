"""
테스트 파이프라인 API — 실제 후처리/검증 함수를 순서대로 실행.
검증 실행부는 app/engine/runner.py 를 공유한다 (검증 탭과 동일 동작).
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
    entries as _entries,
    first_param as _first_param,
    run_validation as _run_validation,
    sig_has as _sig_has,
    timecode as _tc,
    validation_params_for,
)
from app.models import TechItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/test", tags=["test"])


class TestRunRequest(BaseModel):
    srt_text: str
    broadcaster_id: str
    pipeline: list[str]
    params_override: dict = {}


def _run_processing(item, fn, subs, params):
    """후처리: subs 를 변환. (subs, changes) 반환"""
    ft = item.func_type
    before_map = {id(s): s.content for s in subs}

    if ft == "multi_subtitle":
        fp = _first_param(fn)
        kwargs = dict(params)
        result = fn(**{fp: subs, **kwargs}) if fp else fn(subs, **kwargs)
        if isinstance(result, list):
            subs = result
    elif ft == "timing":
        # front/back end 조정
        for i in range(len(subs) - 1):
            kwargs = dict(params)
            if _sig_has(fn, "front_end_time"):
                subs[i].end = fn(front_end_time=subs[i].end, back_start_time=subs[i + 1].start, **kwargs)
    else:  # content_only / content_with_params / content_with_validation_params
        fp = _first_param(fn) or "sentence"
        for s in subs:
            kwargs = dict(params)
            kwargs["subtitle_index"] = s.index
            try:
                s.content = fn(**{fp: s.content, **kwargs})
            except TypeError:
                s.content = fn(s.content)

    # 변경 내역
    changes = []
    for s in subs:
        b = before_map.get(id(s))
        if b is not None and b != s.content:
            changes.append({"index": s.index, "before": b, "after": s.content})
    return subs, changes


@router.post("/run")
def run_test_pipeline(body: TestRunRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # SRT 파싱
    try:
        subs = list(srt.parse(body.srt_text))
    except Exception as e:
        return {"error": f"SRT 파싱 실패: {e}", "steps": []}
    if not subs:
        return {"error": "SRT 파싱 실패: 유효한 자막이 없습니다.", "steps": []}

    parsed_entries = _entries(subs)
    vp = validation_params_for(db, body.broadcaster_id)

    items_map = {}
    if body.pipeline:
        rows = db.query(TechItem).filter(TechItem.id.in_(body.pipeline)).all()
        items_map = {it.id: it for it in rows}

    steps = []
    for si, item_id in enumerate(body.pipeline):
        item = items_map.get(item_id)
        if not item:
            steps.append({"step": si + 1, "item_id": item_id, "item_name": "Unknown", "item_type": "unknown",
                          "status": "error", "result": {"passed": False, "total_entries": len(subs),
                          "error_count": 1, "errors": [{"index": 0, "message": "항목을 찾을 수 없습니다.", "severity": "error"}]}})
            continue

        params = dict(item.params or {})
        if item_id in body.params_override:
            params.update(body.params_override[item_id])

        fn = getattr(rules, item.function_name, None)
        base = {"step": si + 1, "item_id": item.id, "item_name": item.name,
                "item_type": item.type, "params_used": params}

        if fn is None:
            steps.append({**base, "status": "skip", "result": {"passed": True, "total_entries": len(subs),
                          "error_count": 0, "errors": [], "info": f"미구현 함수: {item.function_name}()"}})
            continue

        try:
            if item.type == "processing":
                subs, changes = _run_processing(item, fn, subs, params)
                steps.append({**base, "status": "pass", "result": {
                    "passed": True, "total_entries": len(subs), "error_count": 0, "errors": [],
                    "changes": changes, "info": (f"{len(changes)}개 자막 변경됨" if changes else "변경 없음")}})
            else:
                errors = _run_validation(item, fn, subs, params, vp)
                steps.append({**base, "status": "fail" if errors else "pass", "result": {
                    "passed": len(errors) == 0, "total_entries": len(subs),
                    "error_count": len(errors), "errors": errors[:100],
                    "info": (f"{len(errors)}건 재작업 요청" if errors else "오류 없음")}})
        except Exception as e:
            logger.exception("test step failed")
            steps.append({**base, "status": "error", "result": {"passed": False, "total_entries": len(subs),
                          "error_count": 1, "errors": [{"index": 0, "message": f"실행 오류: {e}", "severity": "error"}],
                          "info": "함수 실행 중 오류"}})

    total_errors = sum(s["result"].get("error_count", 0) for s in steps)
    all_passed = all(s["status"] in ("pass", "skip") for s in steps)

    return {
        "srt_entry_count": len(parsed_entries),
        "pipeline_length": len(body.pipeline),
        "all_passed": all_passed,
        "total_errors": total_errors,
        "entries": parsed_entries,
        "final_entries": _entries(subs),
        "steps": steps,
    }