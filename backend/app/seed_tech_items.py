"""
TechItem 시드 — pipeline_config(= config_subtitle.yml 전사본)에서 파생.

config 에 적힌 순서가 곧 실행 순서이므로, 여기서 만든 순서를 그대로
Mapping.sort_order 로 저장한다. 방송사별 파이프라인은 다음 순서로 구성된다.

    1차 후처리(공통) → 1차 검증(공통)
    → 2차 후처리(공통 − postprocess_remove + postprocess_extend)
    → 2차 검증(공통 − validate_remove + validate_extend)
    → 최종 납품(final_postprocess: 마침표 제거 · 배너)

설명·표시 이름의 근거는 mediaflow docs/subtitle_rules.md 이다.
"""
import inspect

from app.engine import rules
from app.models import TechItem
from app.pipeline_config import BROADCASTER_CODES, FINAL, STAGE1, STAGE2

# 최종 납품 단계는 config 에 함수 목록이 아니라 플래그로 들어 있어서 여기서 함수로 편다.
FINAL_PUNCTUATION_FN = "postprocess_remove_last_punctuation"
FINAL_BANNER_FN = "postprocess_add_banner_subtitle"


# ── 표시 이름 / 설명 ─────────────────────────────────────────────
#   docs/subtitle_rules.md 의 "내용 · 예외 · 동반 처리" 열을 옮긴 것.
FUNCTION_INFO = {
    # 공통 후처리
    "postprocess_remove_delete_tag": (
        "편집자 삭제 마커 처리",
        "{\\ㅅ}: 괄호 안이면 괄호 포함 그룹만 삭제, 괄호 밖이면 자막 자체를 제거. "
        "{\\}: 위치 무관 삭제하며 뒤에 이어지는 마침표·말줄임표도 함께 삭제. {\\ㅅ} → {\\} 순서로 처리."),
    "postprocess_strip_whitespace": ("문장 앞뒤 공백 제거", "문장 앞뒤 공백을 제거한다."),
    "postprocess_trim_speaker_spaces": (
        "괄호 안쪽 공백 제거", "소괄호·대괄호 안쪽의 공백을 제거한다. ( 웃음 ) → (웃음)"),
    "postprocess_add_speaker_space": (
        "화자 뒤 공백 추가", "화자 표시 닫는 괄호 뒤에 글자가 바로 오면 공백을 넣는다. 뒤가 공백·[·( 이면 넣지 않는다."),
    "postprocess_normalize_spaces": ("연속 공백 정규화", "연속 공백을 1칸으로 줄인다. 줄바꿈은 보존."),
    "postprocess_add_space_after_special_punctuation": (
        "특수기호 뒤 공백 추가",
        "...(3개 이상) ? ! 뒤에 글자가 바로 오면 공백을 넣는다. 줄 맨 앞은 제외하고, "
        "숫자 뒤 ~ 는 범위 표현이라 제외한다(1~9 유지)."),
    "postprocess_remove_wrong_punctuation": (
        "문장 앞 잘못된 기호 제거",
        "문장 앞의 . ... ? ! ~ 를 제거하고 문장 끝 쉼표를 삭제한다. ..(2개)는 위치 무관 유지."),
    "postprocess_normalize_ellipsis": (
        "말줄임표 정규화",
        "2개→1개, 3개 유지, 4개→3개, 5개 이상은 유지(검증에서 재작업). 문장 끝 공백도 함께 제거."),
    "postprocess_normalize_repeats": (
        "반복 특수기호 정규화", "! ? , ~ 의 반복을 1개로 줄인다. 마침표는 제외(말줄임표 보존)."),
    "postprocess_normalize_wrong_mixed_punctuations": (
        "잘못된 특수문자 정규화",
        "．→. · →. ‘’→' 로 바꾸고 큰따옴표(\" “ ” ＂)는 삭제한다. 오탈자 보정: 곘→겠, 꼐→께."),
    "postprocess_fix_position_tag": (
        "위치 태그 보정",
        "{\\무8} {\\AN8} {/an8} { n 8 } {무8} 등 위치 태그 오타를 {\\an8}로 보정한다. "
        "양쪽 중괄호가 없거나 닫는 중괄호가 빠지면 일반 텍스트일 수 있어 보정하지 않는다."),
    "postprocess_fix_yae_yee": (
        "ㅒ/ㅖ + ㅆ 보정",
        "중성 ㅒ/ㅖ + 종성 ㅆ → ㅐ/ㅔ (핬→했, 걨→겠). NFD 한글을 NFC로 정규화한다. "
        "중성이 이미 ㅐ면 변환하지 않는다(갰다 유지)."),
    "postprocess_normalize_mix_characters": (
        "혼합 특수기호 정규화",
        "연속 문장부호 런을 정리한다. 마침표만인 런은 말줄임표 규칙에 위임하고, "
        "마침표가 2개 이상 섞이면 ...로, 그 외는 마지막 부호만 남긴다(?!→!, ,.→.)."),
    "postprocess_normalize_comma_space": (
        "쉼표 앞뒤 공백 정규화",
        "쉼표 앞 공백은 삭제하고 뒤는 1칸으로 맞춘다. 뒤에 숫자가 정확히 3개일 때만 "
        "천 단위로 보고 앞뒤 공백을 삭제한다(2, 400억 → 2,400억). 문장 끝 쉼표는 유지."),
    "postprocess_normalize_period_space": (
        "마침표 앞뒤 공백 정규화",
        "마침표 앞 공백은 삭제하고, 뒤에 글자가 이어질 때만 공백 1칸을 넣는다. "
        "문장 끝·닫는 괄호 앞에는 넣지 않고, 숫자 사이 마침표는 앞뒤 공백을 삭제한다(6. 25 → 6.25)."),
    "postprocess_sync_overlap": (
        "싱크 맞닿음 조정",
        "앞.end == 뒤.start 로 맞닿으면 앞 end를 10ms 당긴다. 음수가 되면 0으로 보정. "
        "겹침(오버랩)은 대상이 아니다. 시간을 바꾸므로 1차에서만 실행한다."),
    "postprocess_reset_subtitles_from_list": (
        "정렬 + 인덱스 재부여", "시작 시각 기준으로 정렬하고 인덱스를 1부터 다시 매긴다."),

    # 공통 검증
    "validate_length_lines": ("줄별 글자 수 검증", "줄별 글자 수 초과를 검출한다. 방송사별 가중치를 적용한다(TVNG는 기타 문자 0.5자)."),
    "validate_line_count": ("줄 수 검증", "자막의 줄 수가 방송사 한도를 넘는지 검사한다."),
    "validate_pair_characters": ("괄호/따옴표 짝 검증", "괄호·따옴표·음표의 짝이 맞는지 검사한다. 비대칭 문자는 스택으로 검증한다."),
    "validate_special_characters_allow_music_note": (
        "특수문자 검증 (♪ 허용)", "미허용 특수문자를 검출한다. 음표는 허용하고 슬래시(/)는 불허한다."),
    "validate_special_characters": ("특수문자 검증 (음표 불허)", "미허용 특수문자를 검출한다. 음표도 허용하지 않는다."),
    "validate_empty_content": ("빈 자막 검증", "내용이 비어 있는 자막을 검출한다."),
    "validate_ellipsis_count": (
        "말줄임표 개수 검증", "마침표가 기준 개수 이상 연속되면 검출한다. 2~4개는 후처리로 정리되므로 대상이 아니다."),
    "validate_sync_negative_or_zero": (
        "싱크 역전 검증",
        "시작 시간 ≥ 종료 시간인 자막을 검출한다. 동반 처리로 시작 시간을 종료−0.001로 치환하고 로그에 안내한다."),

    # 2차 방송사별 후처리
    "postprocess_over_length_lines": (
        "글자 수 초과 줄바꿈", "한 줄이 기준 글자 수를 넘으면 공백(어절) 단위로 앞에서부터 채우며 줄을 나눈다. 스타일 태그는 글자 수에서 제외."),
    "postprocess_over_length_lines_middle": (
        "글자 수 초과 줄바꿈 (중앙 분할)",
        "기준 글자 수를 넘으면 중앙에 가장 가까운 공백에서 나눈다. 나눈 줄도 초과하면 반복하고, 공백이 없으면 나누지 않는다."),
    "postprocess_remove_all_star": ("별표 전부 제거", "모든 *를 제거한다(STT 병합 마커). 위치 무관, 앞뒤 문장은 유지한다."),
    "postprocess_remove_other_characters": ("통합 기호 제거", "* ♪ ♫ [] () <> ^ 를 일괄 제거한다."),
    "postprocess_remove_not_pair_characters": ("짝 안 맞는 문자 제거", "짝이 맞지 않는 괄호·따옴표·기호를 제거한다."),
    "postprocess_remove_star_and_angle_for_lghv": ("별표/꺾쇠 제거", "* 와 <> 를 제거한다."),
    "postprocess_remove_star_and_angle_for_skbb": ("미허용 기호 제거", "큰따옴표·음표·소괄호·별표·꺾쇠를 일괄 제거한다."),
    "postprocess_remove_not_pair_paren_quotes_for_lghv": ("짝 안 맞는 괄호/따옴표 제거", "짝이 맞지 않는 괄호·따옴표만 제거한다."),
    "postprocess_remove_not_pair_paren_quotes_for_skbb": ("짝 안 맞는 기호 제거", "짝이 맞지 않는 ' 와 <> 만 제거한다."),
    "postprocess_normalize_music_to_double_note_for_lghv": ("음표 ♫ 통일", "음표를 ♫ 로 통일한다."),
    "postprocess_normalize_music_to_single_note_for_tvng": ("음표 ♪ 통일", "음표를 ♪ 로 통일한다."),
    "postprocess_keep_bracket_music_note_and_remove_others_for_lghv": (
        "[♫ …] 안 음표만 보존", "대괄호 안의 음표만 남기고 나머지 음표를 제거한다."),
    "postprocess_normalize_asterisk_for_skbb": (
        "별표 정규화", "별표가 2개 이상이면 ** 로 통일하고, 1개면 토큰으로 치환한다."),
    "postprocess_remove_first_hypn": ("첫 자막 하이픈 제거", "맨 앞 하이픈을 제거한다. 파일의 첫 자막(index 1)에만 적용한다."),
    "postprocess_remove_space_after_hypn": ("하이픈 뒤 공백 제거", "줄 맨 앞 '- 대사' 를 '-대사' 로 바꾼다."),
    "postprocess_mark_overlapped_multi_speaker": (
        "오버랩 다화자 병합",
        "시간이 겹치는 자막을 하나로 병합하고 화자 구분자를 붙인다. 3개 이상 겹치면 전략에 따라 "
        "가장 많이 겹치는 2개만 병합한다(best_pair). 파일의 첫 자막에는 구분자를 붙이지 않고, "
        "대괄호 태그만인 자막은 병합에서 제외한다."),
    "postprocess_apply_overlap_hyphen_for_all_speech": (
        "오버랩 전체 발화 하이픈",
        "오버랩 그룹에 발화가 2개 이상이면 그룹 내 모든 발화에 '- ' 를 붙인다. 음향 싱크에는 붙이지 않고, "
        "이미 '- ' 로 시작하면 중복 삽입하지 않는다. 허용 총 줄 수는 음향 포함 3줄 / 미포함 2줄."),
    "postprocess_add_period_between_lines": (
        "줄 간 마침표 삽입",
        "한 자막 안에서 뒷 줄이 -/( 로 시작하고 앞 줄이 종결부호로 끝나지 않으면 마침표를 넣는다. "
        "앞이 .!?~ ... ) ] 로 끝나면 건너뛴다."),
    "postprocess_add_period_between_subs": (
        "자막 간 마침표 삽입",
        "뒷 자막이 -/( 로 시작하고 앞 자막이 종결부호로 끝나지 않으면 마침표를 넣는다. "
        "마침표 추가로 글자 수를 초과하면 줄 수 여유가 있을 때만 줄바꿈한다."),
    "postprocess_adjust_subtitle_gaps": (
        "자막 간격 조정",
        "자막 간 간격을 gap_sec 이상으로 보장한다. 간격이 0 이상 gap_sec 미만이면 앞 자막 end를 "
        "다음.start − gap_sec 으로 조정한다. 오버랩(간격 음수)은 건드리지 않고, "
        "오버랩 그룹이 있으면 그룹의 가장 늦은 end 를 기준으로 판정한다."),
    "postprocess_adjust_short_sync": (
        "짧은 자막 연장",
        "min_duration_sec 미만 자막을 늘린다. 간격이 길이보다 우선이라 다음 자막과의 간격을 지킬 수 있는 "
        "최대 지점까지만 연장하므로 기준 미만으로 남을 수 있다(검증이 받아낸다). 마지막 자막은 무조건 연장한다."),

    # 2차 방송사별 검증
    "validate_overlapped_over_lines": ("오버랩 줄 수 검증", "시간이 겹치는 자막의 줄 수가 한도를 넘으면 검출한다."),
    "validate_overlapped_only_text_for_lghv": (
        "오버랩 대괄호 태그 검증", "오버랩된 1줄+1줄 중 하나라도 대괄호 태그만으로 구성되어 있으면 오류로 본다."),
    "validate_overlapped_accumulated_lines": (
        "연속 오버랩 누적 줄 수 검증",
        "연속 오버랩 그룹의 누적 줄 수가 한도를 넘으면 그룹 전체를 오류로 본다. 2개 이상 겹칠 때만 발동한다."),
    "validate_sync_overlapped": ("오버랩 존재 검증", "오버랩(싱크 겹침) 자체를 불허한다."),
    "validate_sync_short_duration": ("최소 자막 길이 검증", "자막 길이가 min_duration_sec 미만이면 검출한다(0초 초과 ~ 기준 미만)."),
    "validate_sync_gap": (
        "자막 간격 검증",
        "자막 간 간격이 gap_sec 미만이면 검출한다. postprocess_adjust_subtitle_gaps 와 동일 기준(그룹 최종 end)이라 "
        "정상 흐름에서는 걸리지 않는 안전망이다. 오버랩·포함 상태는 대상이 아니다."),
    "validate_hyphen_no_space_after_for_skbb": ("하이픈 뒤 공백 검증", "줄 시작 - 뒤에 공백이 오면 오류로 본다."),
    "validate_mosaic_count_for_skbb": ("모자이크 개수 검증", "연속된 * 그룹의 길이가 기준과 다르면 검출한다."),
    "validate_comma_space": (
        "쉼표 공백 검증",
        "쉼표 앞뒤 모두 공백이 없으면 오류로 본다. 한쪽이라도 공백·줄바꿈이 있으면 정상이고, "
        "숫자 사이 쉼표와 문장 끝 쉼표는 정상, 문장 맨 앞 쉼표는 대상이다."),
    "validate_line_count_allow_hyphen": (
        "줄 수 검증 (하이픈 예외)",
        "기본 max_lines 를 넘으면 오류지만, 모든 줄이 - 로 시작하면 max_lines_with_hyphen 까지 허용한다. "
        "일부 줄만 하이픈이면 오류다."),

    # 최종 납품
    FINAL_PUNCTUATION_FN: (
        "마침표 삭제 (납품)",
        "납품 직전 단일 마침표를 제거한다. 말줄임표(...), 숫자.숫자, 영문.영문 은 보존한다."),
    FINAL_BANNER_FN: (
        "배너 자막 삽입 (납품)",
        "장애인방송 제작지원 배너 자막을 맨 앞에 삽입한다. 기본은 설정된 구간을 그대로 쓰고 "
        "자막과 겹쳐도 두지만, gap_before_sec 가 설정된 방송사는 배너 구간 안에서 시작하는 "
        "첫 자막보다 그만큼 앞에서 배너를 끊는다. 첫 자막이 배너 시작과 붙어 있거나 "
        "조정 결과가 min_duration_sec 미만이면 설정값을 그대로 쓴다."),
}


def _info(fn):
    if fn in FUNCTION_INFO:
        return FUNCTION_INFO[fn]
    return fn, ""


def _abbr(fn):
    """함수명 → 4자 이내 약어 (id 생성용)."""
    stem = fn.split("_", 1)[1] if "_" in fn else fn
    return "".join(w[0] for w in stem.split("_") if w)[:4]


class _IdFactory:
    """s2_lghv_apbs 형태의 짧고 안정적인 id 를 만든다 (TechItem.id 는 12자)."""

    def __init__(self):
        self.used = set()

    def make(self, stage_code, scope_code, fn):
        base = f"{stage_code}_{scope_code}_{_abbr(fn)}"
        candidate, n = base, 1
        while candidate in self.used:
            n += 1
            candidate = f"{base[:11 - len(str(n))]}{n}"
        self.used.add(candidate)
        return candidate


def _source_of(fn):
    impl = getattr(rules, fn, None)
    try:
        return inspect.getsource(impl) if impl else ""
    except (OSError, TypeError):
        return ""


def _make_item(item_id, fn, func_type, stage, scope, params, label_prefix=""):
    name, desc = _info(fn)
    return TechItem(
        id=item_id,
        type="validation" if fn.startswith("validate_") else "processing",
        name=f"{label_prefix}{name}",
        function_name=fn,
        func_type=func_type,
        stage=stage,
        desc=desc,
        params=params or {},
        scope=scope,
        tag="applied",
        source_code=_source_of(fn),
    )


def _final_entries(code):
    """final_postprocess 플래그를 실행 가능한 (함수, func_type, params) 목록으로 편다."""
    cfg = FINAL.get(code) or {}
    entries = []
    if cfg.get("remove_punctuation"):
        entries.append((FINAL_PUNCTUATION_FN, "content_with_params",
                        {"punctuation": cfg.get("punctuation_list") or ["."]}))
    if cfg.get("banner"):
        setting = dict(cfg.get("banner_setting") or {})
        entries.append((FINAL_BANNER_FN, "multi_subtitle", setting))
    return entries


def build():
    """
    (items, pipelines) 반환.
      items     : TechItem 목록
      pipelines : {방송사코드: [실행 순서대로의 TechItem.id]}
    """
    ids = _IdFactory()
    items = []
    common_ids = {}   # (stage, kind) → [(function_name, item_id)]

    def add_common(stage_code, stage, kind, entries):
        bucket = []
        for entry in entries or []:
            fn = entry["name"]
            item_id = ids.make(stage_code, "com", fn)
            items.append(_make_item(item_id, fn, entry.get("type", "content_only"),
                                    stage, "common", entry.get("params"),
                                    label_prefix="" if stage == "stage1" else "[공통] "))
            bucket.append((fn, item_id))
        common_ids[(stage, kind)] = bucket

    add_common("s1", "stage1", "postprocess", STAGE1["common"].get("postprocess"))
    add_common("s1", "stage1", "validate", STAGE1["common"].get("validate"))
    add_common("s2", "stage2", "postprocess", STAGE2["common"].get("postprocess"))
    add_common("s2", "stage2", "validate", STAGE2["common"].get("validate"))

    pipelines = {}
    for code in BROADCASTER_CODES:
        cfg = STAGE2.get(code) or {}
        scope_code = code.lower()
        order = [item_id for _, item_id in common_ids[("stage1", "postprocess")]]
        order += [item_id for _, item_id in common_ids[("stage1", "validate")]]

        for kind, stage_kind in (("postprocess", "postprocess"), ("validate", "validate")):
            removed = set(cfg.get(f"{kind}_remove") or [])
            order += [item_id for fn, item_id in common_ids[("stage2", stage_kind)]
                      if fn not in removed]
            for entry in cfg.get(f"{kind}_extend") or []:
                fn = entry["name"]
                item_id = ids.make("s2", scope_code, fn)
                items.append(_make_item(item_id, fn, entry.get("type", "content_only"),
                                        "stage2", "specific", entry.get("params"),
                                        label_prefix=f"[{code}] "))
                order.append(item_id)

        for fn, func_type, params in _final_entries(code):
            item_id = ids.make("s3", scope_code, fn)
            items.append(_make_item(item_id, fn, func_type, "final", "specific", params,
                                    label_prefix=f"[{code}] "))
            order.append(item_id)

        pipelines[code] = order

    return items, pipelines


def get_tech_items():
    return build()[0]
