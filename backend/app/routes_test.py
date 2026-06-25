"""
테스트 파이프라인 API — 실제 후처리/검증 함수를 순서대로 실행.
srt 라이브러리 필요: pip install srt --break-system-packages
"""
import inspect
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

import srt
from app.database import get_db
from app.models import TechItem
from app.auth import get_current_user
from app.engine import rules

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/test", tags=["test"])


# ── 방송사별 검증 파라미터 (config subtitle.validation_params) ────
_COMMON = {"max_length": 18, "max_lines": 2, "max_byte_length": 36, "weight_kor": 1.0, "weight_etc": 1.0}
VALIDATION_PARAMS = {
    "b_jtbc": dict(_COMMON),
    "b_lghv": dict(_COMMON),
    "b_tvcs": dict(_COMMON),
    "b_skbb": {**_COMMON, "max_length": 20, "max_lines": 1, "max_byte_length": 40},
    "b_tvng": {**_COMMON, "max_length": 20, "max_lines": 2, "weight_etc": 0.5},
    "b_dliv": {**_COMMON, "max_length": 17, "max_lines": 3, "max_byte_length": 34},
}


class TestRunRequest(BaseModel):
    srt_text: str
    broadcaster_id: str
    pipeline: list[str]
    params_override: dict = {}


def _tc(sub) -> str:
    return f"{srt.timedelta_to_srt_timestamp(sub.start)} --> {srt.timedelta_to_srt_timestamp(sub.end)}"


def _entries(subs):
    return [{"index": s.index, "timecode": _tc(s), "text": s.content} for s in subs]


def _first_param(fn):
    try:
        return list(inspect.signature(fn).parameters.keys())[0]
    except Exception:
        return None


def _sig_has(fn, name):
    try:
        return name in inspect.signature(fn).parameters
    except Exception:
        return False


# 검증 함수 → 읽기 좋은 메시지
def _detail(item, vp):
    fn = item.function_name
    p = item.params or {}
    table = {
        "validate_length_lines": f"한 줄 {vp.get('max_length', 18)}자 초과",
        "validate_line_count": f"{vp.get('max_lines', 2)}줄 초과",
        "validate_pair_characters": "괄호/따옴표/음표 짝 불일치",
        "validate_special_characters_allow_music_note": "사용 불가 특수문자 포함 (\u266a 제외)",
        "validate_special_characters": "사용 불가 특수문자 포함",
        "validate_sync_negative_or_zero": "시작 시간 >= 종료 시간",
        "validate_ellipsis_count": f"마침표 {p.get('criterion', 2)}개 연속",
        "validate_hyphen_no_space_after_for_skbb": "하이픈 뒤 공백 없음",
        "validate_mosaic_count_for_skbb": f"모자이크(*) 개수 오류 (기준 {p.get('criterion', 2)}개)",
        "validate_overlapped_over_lines": f"오버랩 + {p.get('max_lines', 2)}줄 이상",
        "validate_overlapped_only_text_for_lghv": "오버랩 + 대괄호 태그",
        "validate_sync_overlapped": "오버랩(싱크 겹침) 미허용",
        "validate_sync_short_duration": f"자막 길이 {p.get('min_duration_sec', 1.0)}초 미만",
        "validate_comma_space": "쉼표(,) 앞뒤 공백 없음",
        "validate_overlapped_accumulated_lines": f"연속 오버랩 누적 {p.get('max_lines', vp.get('max_lines', 3))}줄 초과",
    }
    return table.get(fn, f"{item.name} 위반")


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


def _run_validation(item, fn, subs, params, vp):
    """검증: 오류 리스트 반환 (재작업 대상)"""
    ft = item.func_type
    errors = []
    msg = _detail(item, vp)

    if ft == "multi_validation":
        kwargs = {**vp, **params}
        res = fn(subs, **kwargs)
        if isinstance(res, dict):
            for idx, det in res.items():
                s = next((x for x in subs if x.index == idx), None)
                errors.append({"index": idx, "type": item.function_name, "severity": "error",
                               "message": det or msg, "timecode": _tc(s) if s else "",
                               "text": s.content if s else ""})
    elif ft == "pair_validation":
        for i in range(len(subs) - 1):
            try:
                bad = fn(front_content=subs[i].content, back_content=subs[i + 1].content,
                         front_end_time=subs[i].end, back_start_time=subs[i + 1].start, **params)
            except TypeError:
                bad = fn(subs[i].content, subs[i + 1].content, subs[i].end, subs[i + 1].start)
            if bad:
                s = subs[i]
                errors.append({"index": s.index, "type": item.function_name, "severity": "error",
                               "message": msg, "timecode": _tc(s), "text": s.content})
    elif ft == "timing" or _sig_has(fn, "start_time"):
        for s in subs:
            if fn(start_time=s.start, end_time=s.end, **params):
                errors.append({"index": s.index, "type": item.function_name, "severity": "error",
                               "message": msg, "timecode": _tc(s), "text": s.content})
    else:  # content 계열
        # 길이 검증은 줄별 글자수 상세 제공
        if item.function_name == "validate_length_lines":
            ml = params.get("max_length", vp.get("max_length", 18))
            wk = vp.get("weight_kor", 1.0); we = vp.get("weight_etc", 1.0)
            for s in subs:
                for li, line in enumerate(s.content.split("\n")):
                    plain = rules.strip_style_tags(line)
                    cnt = len(plain) if (wk == 1.0 and we == 1.0) else sum(wk if "\uac00" <= c <= "\ud7a3" else we for c in plain)
                    if cnt > ml:
                        errors.append({"index": s.index, "type": "CHAR_OVERFLOW", "severity": "error",
                                       "message": f"글자 수 초과 (Line {li + 1})", "timecode": _tc(s),
                                       "text": line, "char_count": int(cnt), "limit": ml})
        else:
            kwargs = {**vp, **params}
            for s in subs:
                try:
                    bad = fn(s.content, **kwargs)
                except TypeError:
                    bad = fn(s.content)
                if bad:
                    errors.append({"index": s.index, "type": item.function_name, "severity": "error",
                                   "message": msg, "timecode": _tc(s), "text": s.content})
    return errors


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
    vp = VALIDATION_PARAMS.get(body.broadcaster_id, _COMMON)

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