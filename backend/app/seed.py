"""
초기 데이터 시드 (정책 매트릭스 + config 기반 파이프라인).

정책 매트릭스는 자막팀이 관리하는 "무엇을 지켜야 하나"이고,
TechItem / Mapping 은 config_subtitle.yml 이 실제로 "무엇을 돌리나"이다.
둘이 어긋난 곳은 정책 쪽 detail 에 실제 동작을 함께 적어 둔다.
"""
from sqlalchemy.orm import Session

from app.accounts import get_users
from app.auth import hash_password
from app.models import (
    Broadcaster, ItemTechLink, Mapping, PolicyCategory, PolicyItem, PolicyValue,
    User, gen_id,
)
from app.seed_tech_items import build


# 방송사 — config_subtitle.yml 의 코드 기준. TVING 은 config 상 코드가 TVNG 다.
BROADCASTERS = [
    ("b_jtbc", "JTBC", "JTBC", "#db2777"),
    ("b_lghv", "LGHV", "LGHV", "#dc2626"),
    ("b_skbb", "SKBB", "SKBB", "#f97316"),
    ("b_tvcs", "TVCS", "TVCS", "#8b5cf6"),
    ("b_dliv", "DLIV", "DLIV", "#3b82f6"),
    ("b_tvng", "TVNG", "TVING", "#b91c1c"),
    ("b_kbs", "KBS", "KBS", "#0ea5e9"),
]
BC = {code: bid for bid, code, _, _ in BROADCASTERS}


# ── 엑셀 시트 → 정책 매트릭스 ──────────────────────────────────────
#   구조: (카테고리, [ (항목명, 설명, { 방송사: (summary, detail) }) ])
#   summary = 전체 탭용 짧은 값 (O / X / △ / 18글자 …)
#   detail  = 방송사별 탭용 풀어쓴 전문 (없으면 빈 문자열)
POLICY_MATRIX = [
    ("싱크", [
        ("일반", "영상 내 음성에 맞게 싱크 생성/조정 작업", {
            "DLIV": ("O", "싱크 시작 지점을 정확하게 보정 (자막 시작이 음성보다 빠르지 않도록)"),
            "LGHV": ("O", ""), "SKBB": ("O", ""), "JTBC": ("O", ""),
            "TVCS": ("O", ""), "TVNG": ("O", ""), "KBS": ("O", ""),
        }),
        ("오버랩", "영상 내 음성이 겹치는 경우 오버랩 작업", {
            "DLIV": ("O", "오버랩을 의도적으로 사용한다. 병합하지 않고 그대로 납품 "
                          "(postprocess_mark_overlapped_multi_speaker 비활성). "
                          "누적 줄 수 3줄 초과만 validate_overlapped_accumulated_lines 로 잡는다"),
            "LGHV": ("O", "대사(1줄)+대사(1줄)만 가능. 구분자 기본값('- '), 3개 이상 겹치면 "
                          "가장 많이 겹치는 2개만 병합(best_pair)"),
            "SKBB": ("X", "오버랩 자체 불허 — validate_sync_overlapped"),
            "JTBC": ("O", "대사(1줄)+대사(1줄)만 가능. 3인 이상 시 우선순위 작업 후 나머지 버림(best_pair)"),
            "TVCS": ("X", "오버랩 자체 불허 — validate_sync_overlapped"),
            "TVNG": ("O", "대사+대사 / 대사+음향 등 조합 가능. 병합 후에도 그룹 내 모든 발화에 '- ' 부착"),
            "KBS": ("O", "병합 후 최대 2줄. 구분자 '-'(공백 없음), 3개 이상 겹치면 best_pair"),
        }),
        ("배경음악", "배경음악 별도 표기", {
            "DLIV": ("X", "배경음악 표기 없음"),
            "LGHV": ("O", "[배경음악] 표기"),
            "SKBB": ("X", ""), "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVNG": ("O", "[음악: '제목' OST] 또는 [ㅇㅇ한 음악] 표기. 제목은 티빙 제공 제목과 동일하게"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("음향/효과음", "효과음 별도 표기", {
            "DLIV": ("O", "(ㅇㅇ 소리) 표기, (노래 전주) 표기"),
            "LGHV": ("O", "[ㅇㅇ 소리] 표기. 명확한 표현이 가능한 소리 (예: [휘파람 소리])"),
            "SKBB": ("O", "[ㅇㅇ 소리], [노래 전주], [웃음소리], [울음소리]"),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVNG": ("O", "명확/불명확 소리 표기 규칙. 화면에 보이면 미기입. 배경음 지속 시 [-계속]"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("OC 자막 (100% 동일)", "OC 자막과 음성이 100% 동일한 경우 텍스트 작업", {
            "DLIV": ("X", "100% 동일한 경우 자막 생략"),
            "LGHV": ("△", "동일한 텍스트 작업 진행 (조건부)"),
            "SKBB": ("△", "동일한 텍스트 작업 진행 (조건부)"),
            "JTBC": ("X", "해당 부분 자막 삭제"),
            "TVCS": ("O", "동일한 텍스트 작업 진행"),
            "TVNG": ("X", "동일한 텍스트 작업 진행"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("OC 자막 (의미 동일)", "OC 자막과 음성의 의미가 동일한 경우 텍스트 작업", {
            "DLIV": ("O", ""), "LGHV": ("△", ""), "SKBB": ("△", ""),
            "JTBC": ("", ""), "TVCS": ("", ""), "TVNG": ("", ""), "KBS": ("", ""),
        }),
        ("자막 간 최소 간격", "자막과 자막 사이에 보장해야 하는 최소 간격", {
            "DLIV": ("0.083초", "24fps 2프레임. postprocess_adjust_subtitle_gaps 로 보장하고 "
                                "validate_sync_gap 이 안전망. 오버랩 구간은 대상 아님"),
            "LGHV": ("—", "간격 규칙 없음. 맞닿은 자막만 1차에서 10ms 당김(postprocess_sync_overlap)"),
            "SKBB": ("—", ""), "JTBC": ("—", ""), "TVCS": ("—", ""),
            "TVNG": ("—", ""), "KBS": ("—", ""),
        }),
        ("최소 자막 길이", "자막 하나가 노출되는 최소 시간", {
            "DLIV": ("1초", "postprocess_adjust_short_sync 로 연장하되 다음 자막과의 간격이 우선이라 "
                            "1초 미만으로 남을 수 있고, validate_sync_short_duration 이 받아낸다"),
            "LGHV": ("—", ""), "SKBB": ("—", ""), "JTBC": ("—", ""),
            "TVCS": ("—", ""), "TVNG": ("—", ""), "KBS": ("—", ""),
        }),
    ]),
    ("텍스트", [
        ("공통", "들리는 음성 기준 텍스트 수정. 문장부호 규칙·추임새 생략", {
            "DLIV": ("O", "마침표(.), 말줄임표(...), 물음표(?) 기입. 느낌표/물결/쉼표/인용 작은따옴표는 자제. 불필요한 추임새 생략 가능"),
            "LGHV": ("O", ""), "SKBB": ("O", ""), "JTBC": ("O", ""),
            "TVCS": ("O", ""), "TVNG": ("O", ""), "KBS": ("O", ""),
        }),
        ("글자 수", "자막 한 줄당 최대 글자 수 (config validation_params.max_length)", {
            "DLIV": ("17글자", ""), "LGHV": ("18글자", ""), "SKBB": ("20글자", ""),
            "JTBC": ("18글자", ""), "TVCS": ("18글자", ""), "TVNG": ("20글자", ""),
            "KBS": ("20글자", ""),
        }),
        ("줄 수", "자막당 최대 줄 수 (config validation_params.max_lines)", {
            "DLIV": ("3줄", ""), "LGHV": ("2줄", ""), "SKBB": ("1줄", ""),
            "JTBC": ("2줄", ""), "TVCS": ("2줄", ""),
            "TVNG": ("2줄", "오버랩 그룹 전체 허용 줄 수는 음향 포함 3줄 / 미포함 2줄"),
            "KBS": ("1줄", "모든 줄이 '-' 로 시작하면 2줄까지 허용 — validate_line_count_allow_hyphen. "
                           "일부 줄만 하이픈이면 오류"),
        }),
        ("바이트 수", "한 줄 최대 바이트 (config validation_params.max_byte_length)", {
            "DLIV": ("34바이트", ""), "LGHV": ("36바이트", ""), "SKBB": ("40바이트", ""),
            "JTBC": ("36바이트", ""), "TVCS": ("36바이트", ""), "TVNG": ("36바이트", ""),
            "KBS": ("40바이트", ""),
        }),
        ("글자 수 가중치", "글자 수 계산 시 한글 / 기타 문자에 적용하는 가중치", {
            "DLIV": ("1.0 / 1.0", ""), "LGHV": ("1.0 / 1.0", ""), "SKBB": ("1.0 / 1.0", ""),
            "JTBC": ("1.0 / 1.0", ""), "TVCS": ("1.0 / 1.0", ""),
            "TVNG": ("1.0 / 0.5", "영문·기호를 0.5자로 계산한다"),
            "KBS": ("1.0 / 1.0", ""),
        }),
        ("노래 가사", "출연자가 실제 노래를 부르는 경우 별도 표기", {
            "DLIV": ("O", "OC 자막 존재 시 삭제. 일반 대사와 동일하게 표기"),
            "LGHV": ("O", "[노래 가사] 표기. 음표는 ♫ 로 통일하고 [♫ …] 밖의 음표는 제거"),
            "SKBB": ("O", "최초 1회만 앞에 '-[노래]' 표기. 음표는 후처리에서 제거되고 검증에서도 불허"),
            "JTBC": ("X", "음표 일괄 제거"), "TVCS": ("X", ""),
            "TVNG": ("O", "♪ 노래가사 ♪ 표기 (음표 ♪ 로 통일)"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("화자 구분", "발화자가 변경된 경우 별도 표기", {
            "DLIV": ("O", "하이픈(-) 표기, 뒤 띄어쓰기 없음, 첫 발화부터. "
                          "예외) 해설: -(해설)V발화 / 3인 이상 동시발화: -(같이)V발화"),
            "LGHV": ("△", "작업자가 직접 넣지는 않지만, 오버랩 병합 시 시스템이 기본 구분자 '- ' 를 붙인다"),
            "SKBB": ("O", "하이픈 표기 (띄어쓰기 X). 두 번째 발화자부터 기입. 첫 자막의 맨 앞 하이픈은 제거"),
            "JTBC": ("△", "오버랩 병합 시 시스템이 기본 구분자를 붙인다"),
            "TVCS": ("X", ""),
            "TVNG": ("△", "오버랩 그룹의 모든 발화에 '- '(공백 있음) 부착. 음향 자막에는 붙이지 않음"),
            "KBS": ("△", "오버랩 병합 시 구분자 '-'(공백 없음). 파일의 첫 자막에는 붙이지 않음"),
        }),
        ("비하인드/예고편", "콘텐츠 메인 앞뒤로 추가된 영상의 텍스트 작업", {
            "DLIV": ("O", "텍스트 작업과 동일하게 진행"),
            "LGHV": ("X", "해당 부분 자막 삭제"),
            "SKBB": ("O", "텍스트 작업과 동일하게 진행"),
            "JTBC": ("X", "해당 부분 자막 삭제"), "TVCS": ("X", "해당 부분 자막 삭제"),
            "TVNG": ("O", "텍스트 작업과 동일하게 진행"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("외국어 (문장)", "한국어가 아닌 외국어 문장의 텍스트 작업", {
            "DLIV": ("X", "샘플 내 사례 없음 → LGHV/SKBB 동일 가이드 적용 (외국어 문장 삭제)"),
            "LGHV": ("X", ""), "SKBB": ("X", ""), "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVNG": ("O", "[언어명]만 작성 (예: [영어])"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("외국어 (단어 포함)", "한국어 대사 중 외국어 단어가 포함된 경우 텍스트 작업", {
            "DLIV": ("O", "한국어 문장 내 영어단어·스펠링은 표기. 영어 문장은 별도 표기 안 함"),
            "LGHV": ("O", ""), "SKBB": ("O", ""), "JTBC": ("O", ""),
            "TVCS": ("O", ""), "TVNG": ("O", ""), "KBS": ("O", ""),
        }),
        ("묵음 처리", "비속어/상표 등 가공된 효과음 별도 표기", {
            "DLIV": ("X", "음절별 숫자 '0' 표기"),
            "LGHV": ("X", ""),
            "SKBB": ("O", "글자수 관계없이 2개의 별표(**) 표기. 연속 * 그룹이 2개가 아니면 오류"),
            "JTBC": ("X", ""), "TVCS": ("X", "별표는 STT 병합 마커로 보고 전부 제거"),
            "TVNG": ("O", "삐 소리 음절마다 별표(*) 표기. 전체 문장 삐 처리는 [음소거 효과음]만 표기"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("쉼표 표기", "쉼표 앞뒤 공백 규칙", {
            "DLIV": ("공통", ""), "LGHV": ("공통", ""), "SKBB": ("공통", ""),
            "JTBC": ("공통", ""), "TVCS": ("공통", ""),
            "TVNG": ("검증", "쉼표 앞뒤가 모두 공백 없이 붙어 있으면 오류 — validate_comma_space"),
            "KBS": ("공통", ""),
        }),
    ]),
    ("배리어 프리", [
        ("화자 표기", "화면만으로 화자 식별 불가 시 화자 표기", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVNG": ("O", "텍스트 맨 앞에 (화자)+띄어쓰기 표기"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("효과음 (편집 삽입)", "편집 시 삽입한 인위적 소리 별도 표기", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVNG": ("O", "[OO 효과음] 표기"),
            "KBS": ("", "가이드 미확인"),
        }),
        ("자막 위치", "OC 자막을 가리지 않게 자막 위치 변경", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("X", ""), "TVCS": ("X", ""), "TVNG": ("X", ""), "KBS": ("X", ""),
        }),
    ]),
    ("수급 / 납품", [
        ("자막 형식", "최종 납품 자막의 파일 형식 (config final_postprocess.delivery_extension)", {
            "DLIV": ("srt", ""), "LGHV": ("srt", ""), "SKBB": ("smi", ""),
            "JTBC": ("srt", ""), "TVCS": ("vtt", ""), "TVNG": ("vtt", ""),
            "KBS": ("srt", ""),
        }),
        ("마침표 삭제", "최종 납품 자막의 마침표 삭제 여부", {
            "DLIV": ("X", ""), "LGHV": ("O", ""), "SKBB": ("X", ""),
            "JTBC": ("O", ""), "TVCS": ("X", ""), "TVNG": ("O", ""), "KBS": ("O", ""),
        }),
        ("배너 삽입", "장애인방송 제작지원 배너 자막 노출 구간", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("0:00~5:00", ""), "TVCS": ("0:00~0:07", ""),
            "TVNG": ("X", ""), "KBS": ("0:00~0:05", ""),
        }),
        ("수급 방식", "영상 파일 전달 방식", {
            "DLIV": ("구글 드라이브", "세팅 후 전달 예정"),
            "LGHV": ("구글 드라이브", ""), "SKBB": ("구글 드라이브", ""),
            "JTBC": ("", ""), "TVCS": ("", ""), "TVNG": ("", ""), "KBS": ("", ""),
        }),
        ("납품 방식", "자막 파일 전달 방식", {
            "DLIV": ("구글 드라이브", "세팅 후 전달 예정"),
            "LGHV": ("자체 프로그램", ""), "SKBB": ("이메일", ""),
            "JTBC": ("", ""), "TVCS": ("", ""), "TVNG": ("", ""), "KBS": ("", ""),
        }),
    ]),
]


# ── 정책 항목 ↔ 기술 항목 연결 (3번 페이지용) ──────────────────────
#   함수명으로 지정한다. 같은 함수가 여러 방송사에 등록돼 있으면 전부 연결되므로
#   방송사가 추가돼도 이 표는 손댈 필요가 없다.
#   (정책 항목명, [함수명 …], 연결 설명)
ITEM_TECH_LINKS = [
    ("글자 수", ["validate_length_lines", "postprocess_over_length_lines",
               "postprocess_over_length_lines_middle"],
     "줄별 길이 검증 및 글자 수 초과 줄바꿈"),
    ("줄 수", ["validate_line_count", "validate_line_count_allow_hyphen"], "자막 줄 수 검증"),
    ("바이트 수", ["validate_length_lines"], "바이트 길이도 같은 검증 함수가 담당(valid_type)"),
    ("글자 수 가중치", ["validate_length_lines"], "weight_kor / weight_etc 적용 지점"),
    ("오버랩", ["postprocess_mark_overlapped_multi_speaker",
              "postprocess_apply_overlap_hyphen_for_all_speech",
              "validate_overlapped_over_lines", "validate_overlapped_only_text_for_lghv",
              "validate_overlapped_accumulated_lines", "validate_sync_overlapped"],
     "오버랩 병합 처리 및 오버랩 관련 검증"),
    ("일반", ["postprocess_sync_overlap", "validate_sync_negative_or_zero"],
     "맞닿은 싱크 조정 · 싱크 역전 검증"),
    ("자막 간 최소 간격", ["postprocess_adjust_subtitle_gaps", "validate_sync_gap"],
     "자막 간 간격 보장 및 안전망 검증"),
    ("최소 자막 길이", ["postprocess_adjust_short_sync", "validate_sync_short_duration"],
     "짧은 자막 연장 및 검증"),
    ("화자 구분", ["postprocess_remove_first_hypn", "postprocess_remove_space_after_hypn",
               "postprocess_add_period_between_lines", "postprocess_add_period_between_subs",
               "validate_hyphen_no_space_after_for_skbb"],
     "하이픈 화자 표기 처리 · 검증, 화자 전환 앞 마침표 삽입"),
    ("노래 가사", ["postprocess_normalize_music_to_double_note_for_lghv",
               "postprocess_normalize_music_to_single_note_for_tvng",
               "postprocess_keep_bracket_music_note_and_remove_others_for_lghv"],
     "음표 표기 정규화"),
    ("음향/효과음", ["validate_special_characters_allow_music_note", "validate_special_characters"],
     "음표 허용 여부에 따른 특수문자 검증"),
    ("묵음 처리", ["postprocess_normalize_asterisk_for_skbb", "postprocess_remove_all_star",
               "validate_mosaic_count_for_skbb"],
     "별표(모자이크) 처리 · 검증"),
    ("공통", ["postprocess_remove_delete_tag", "postprocess_strip_whitespace",
            "postprocess_normalize_spaces", "postprocess_trim_speaker_spaces",
            "postprocess_add_speaker_space", "postprocess_add_space_after_special_punctuation",
            "postprocess_remove_wrong_punctuation", "postprocess_normalize_ellipsis",
            "postprocess_normalize_repeats", "postprocess_normalize_wrong_mixed_punctuations",
            "postprocess_normalize_mix_characters", "postprocess_fix_position_tag",
            "postprocess_fix_yae_yee", "postprocess_normalize_comma_space",
            "postprocess_normalize_period_space", "postprocess_reset_subtitles_from_list",
            "validate_pair_characters", "validate_empty_content", "validate_ellipsis_count"],
     "1·2차 공통 표기 정리 및 검증"),
    ("쉼표 표기", ["postprocess_normalize_comma_space", "validate_comma_space"],
     "쉼표 앞뒤 공백 정규화 · 검증"),
    ("외국어 (문장)", ["validate_special_characters", "validate_special_characters_allow_music_note"],
     "허용 문자 범위 검증"),
    ("마침표 삭제", ["postprocess_remove_last_punctuation"], "납품 직전 단일 마침표 제거"),
    ("배너 삽입", ["postprocess_add_banner_subtitle"], "납품 배너 자막 삽입"),
]


def seed(db: Session):
    if db.query(User).first():
        return

    # ── Users ── (AIRRULE_USERS 환경변수, 없으면 로컬 개발용 기본값)
    db.add_all([
        User(id=f"u_{u['username']}", username=u["username"],
             hashed_password=hash_password(u["password"]),
             name=u["name"], role=u["role"])
        for u in get_users()
    ])

    # ── Broadcasters ──
    db.add_all([Broadcaster(id=bid, code=code, name=name, color=color)
                for bid, code, name, color in BROADCASTERS])

    # ── Policy Matrix ──
    item_lookup = {}
    for ci, (cat_name, items) in enumerate(POLICY_MATRIX):
        cat = PolicyCategory(id=gen_id(), name=cat_name, sort_order=ci)
        db.add(cat)
        db.flush()
        for ii, (item_name, desc, vals) in enumerate(items):
            item = PolicyItem(id=gen_id(), category_id=cat.id, name=item_name, description=desc, sort_order=ii)
            db.add(item)
            db.flush()
            item_lookup[item_name] = item
            for code, (summary, detail) in vals.items():
                db.add(PolicyValue(id=gen_id(), item_id=item.id, broadcaster_id=BC[code],
                                   summary=summary, detail=detail))
    db.flush()

    # ── Tech Items + 방송사별 파이프라인 (config 순서 그대로) ──
    tech_items, pipelines = build()
    db.add_all(tech_items)
    db.flush()

    for bid, code, _, _ in BROADCASTERS:
        for order, item_id in enumerate(pipelines.get(code, [])):
            db.add(Mapping(id=gen_id(), broadcaster_id=bid, item_id=item_id, sort_order=order))

    # ── Item ↔ Tech links (함수명 → 해당 함수를 쓰는 모든 TechItem) ──
    by_function = {}
    for ti in tech_items:
        by_function.setdefault(ti.function_name, []).append(ti.id)

    for item_name, function_names, note in ITEM_TECH_LINKS:
        item = item_lookup.get(item_name)
        if not item:
            continue
        for fn in function_names:
            for tid in by_function.get(fn, []):
                db.add(ItemTechLink(id=gen_id(), policy_item_id=item.id,
                                    tech_item_id=tid, note=note))

    db.commit()
    print(f"✅ Seed 완료 — 방송사 {len(BROADCASTERS)} / 기술항목 {len(tech_items)} / "
          f"파이프라인 {sum(len(p) for p in pipelines.values())}단계")
