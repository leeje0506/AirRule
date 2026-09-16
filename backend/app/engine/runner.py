"""
검증 함수 실행 공통부 — 테스트 파이프라인(routes_test)과 검증 탭(routes_validate)이 함께 쓴다.

후처리 실행은 파이프라인 쪽에만 필요해서 routes_test 에 남겨 뒀다.
"""
import inspect

import srt
from sqlalchemy.orm import Session

from app.engine import rules
from app.models import Broadcaster
from app.pipeline_config import BROADCASTER_CODES, VALIDATION_PARAMS

# ── 방송사별 검증 파라미터 ───────────────────────────────────────
#   config_subtitle.yml 의 subtitle.validation_params.
#   방송사 항목은 공통값 위에 덮어쓰는 형태(빈 dict 면 공통값 그대로).
COMMON_PARAMS = dict(VALIDATION_PARAMS["common"])
PARAMS_BY_CODE = {
    code: {**COMMON_PARAMS, **(VALIDATION_PARAMS.get(code) or {})}
    for code in BROADCASTER_CODES
}


def validation_params_for(db: Session, broadcaster_id: str) -> dict:
    bc = db.query(Broadcaster).filter(Broadcaster.id == broadcaster_id).first()
    if bc is None:
        return dict(COMMON_PARAMS)
    return PARAMS_BY_CODE.get(bc.code, dict(COMMON_PARAMS))


# ── 자막 표현 ────────────────────────────────────────────────────

def timecode(sub) -> str:
    return f"{srt.timedelta_to_srt_timestamp(sub.start)} --> {srt.timedelta_to_srt_timestamp(sub.end)}"


def entries(subs):
    return [{"index": s.index, "timecode": timecode(s), "text": s.content} for s in subs]


def first_param(fn):
    try:
        return list(inspect.signature(fn).parameters.keys())[0]
    except Exception:
        return None


def sig_has(fn, name) -> bool:
    try:
        return name in inspect.signature(fn).parameters
    except Exception:
        return False


# ── 검증 함수 → 읽기 좋은 메시지 ─────────────────────────────────

def detail_message(item, vp: dict) -> str:
    fn = item.function_name
    p = item.params or {}
    table = {
        "validate_length_lines": f"한 줄 {vp.get('max_length', 18)}자 초과",
        "validate_line_count": f"{vp.get('max_lines', 2)}줄 초과",
        "validate_pair_characters": "괄호/따옴표/음표 짝 불일치",
        "validate_special_characters_allow_music_note": "사용 불가 특수문자 포함 (♪ 제외)",
        "validate_special_characters": "사용 불가 특수문자 포함",
        "validate_sync_negative_or_zero": "시작 시간 >= 종료 시간",
        "validate_ellipsis_count": f"마침표 {p.get('criterion', 5)}개 이상 연속",
        "validate_hyphen_no_space_after_for_skbb": "줄 시작 하이픈(-) 뒤에 공백 있음",
        "validate_mosaic_count_for_skbb": f"모자이크(*) 연속 개수가 기준({p.get('criterion', 2)}개)과 다름",
        "validate_overlapped_over_lines": f"오버랩 + {p.get('max_lines', 2)}줄 이상",
        "validate_overlapped_only_text_for_lghv": "오버랩 + 대괄호 태그",
        "validate_sync_overlapped": "오버랩(싱크 겹침) 미허용",
        "validate_sync_short_duration": f"자막 길이 {p.get('min_duration_sec', 1.0)}초 미만",
        "validate_comma_space": "쉼표(,) 앞뒤 공백 없음",
        "validate_overlapped_accumulated_lines": f"연속 오버랩 누적 {p.get('max_lines', vp.get('max_lines', 3))}줄 초과",
        "validate_sync_gap": f"다음 자막과 간격 {p.get('gap_sec', 0.083)}초 미만",
        "validate_empty_content": "자막 내용 없음",
        "validate_line_count_allow_hyphen": (
            f"{p.get('max_lines', 1)}줄 초과 (모든 줄이 - 로 시작하면 {p.get('max_lines_with_hyphen', 2)}줄까지 허용)"
        ),
    }
    return table.get(fn, f"{item.name} 위반")


def weighted_length(line: str, vp: dict) -> float:
    """방송사 가중치를 적용한 글자 수. 스타일 태그는 제외한다."""
    plain = rules.strip_style_tags(line)
    wk = vp.get("weight_kor", 1.0)
    we = vp.get("weight_etc", 1.0)
    if wk == 1.0 and we == 1.0:
        return float(len(plain))
    return sum(wk if "가" <= c <= "힣" else we for c in plain)


# ── 검증 실행 ────────────────────────────────────────────────────

def run_validation(item, fn, subs, params: dict, vp: dict):
    """검증 함수 하나를 자막 전체에 돌려 오류 목록을 반환한다 (재작업 대상)."""
    ft = item.func_type
    errors = []
    msg = detail_message(item, vp)

    if ft == "multi_validation":
        kwargs = {**vp, **params}
        res = fn(subs, **kwargs)
        if isinstance(res, dict):
            for idx, det in res.items():
                s = next((x for x in subs if x.index == idx), None)
                errors.append({"index": idx, "type": item.function_name, "severity": "error",
                               "message": det or msg, "timecode": timecode(s) if s else "",
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
                               "message": f"{msg} (다음 자막 #{subs[i + 1].index} 와)",
                               "timecode": timecode(s), "text": s.content})
    elif ft == "timing" or sig_has(fn, "start_time"):
        for s in subs:
            if fn(start_time=s.start, end_time=s.end, **params):
                errors.append({"index": s.index, "type": item.function_name, "severity": "error",
                               "message": msg, "timecode": timecode(s), "text": s.content})
    else:  # content 계열
        # 길이 검증은 어느 줄이 몇 자인지까지 알려준다
        if item.function_name == "validate_length_lines":
            limit = params.get("max_length", vp.get("max_length", 18))
            for s in subs:
                for li, line in enumerate(s.content.split("\n")):
                    count = weighted_length(line, vp)
                    if count > limit:
                        errors.append({"index": s.index, "type": "CHAR_OVERFLOW", "severity": "error",
                                       "message": f"글자 수 초과 (Line {li + 1})", "timecode": timecode(s),
                                       "text": line, "line": li + 1,
                                       "char_count": round(count, 1), "limit": limit})
        else:
            kwargs = {**vp, **params}
            for s in subs:
                try:
                    bad = fn(s.content, **kwargs)
                except TypeError:
                    bad = fn(s.content)
                if bad:
                    errors.append({"index": s.index, "type": item.function_name, "severity": "error",
                                   "message": msg, "timecode": timecode(s), "text": s.content})
    return errors
