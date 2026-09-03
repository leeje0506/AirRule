"""
AirRule 테스트 엔진 — mediaflow utils/subtitle/rules/* 원본 이식본.

⚠️  이 파일은 backend/tools/sync_from_mediaflow.py 가 생성합니다. 직접 수정하지 마세요.
    mediaflow 원본: validate_common.py, postprocess_common.py, postprocess_stage2.py, validate_stage2.py, postprocess_final.py
    동기화 날짜: 2026-09-03

subtitle_common 의존부는 아래 shim 으로 대체했습니다.
필요 패키지: pip install srt
"""
import logging
import re
import string
import unicodedata
from datetime import timedelta
from typing import Dict, List, Optional

import srt

logger = logging.getLogger(__name__)


# ============================================================
# subtitle_common shim
# ============================================================

STYLE_TAG_PATTERN = re.compile(r"\{\\[^}]*\}")


def strip_style_tags(text: str) -> str:
    """스타일 태그({\\an8} 등) 제거 — 글자 수 측정용."""
    if not text:
        return text or ""
    return STYLE_TAG_PATTERN.sub("", text)


def replace_linebreak(content: str, rep_char: str = " ") -> str:
    if content is None:
        return ""
    return content.replace("\n", rep_char)


def set_origin_indices(subtitle, origin_indices) -> None:
    subtitle._origin_indices = sorted(set(origin_indices))


def get_origin_indices(subtitle):
    if not hasattr(subtitle, "_origin_indices"):
        subtitle._origin_indices = [subtitle.index]
    return subtitle._origin_indices


def format_indices(indices) -> str:
    if not indices:
        return "-"
    indices = sorted(set(indices))
    if len(indices) == 1:
        return str(indices[0])
    return ",".join(str(i) for i in indices)


def parse_srt_time(time_str: str) -> timedelta:
    s = (time_str or "").strip().replace(".", ",")
    hms, _, ms = s.partition(",")
    parts = hms.split(":")
    while len(parts) < 3:
        parts.insert(0, "0")
    h, m, sec = parts[-3:]
    ms = ((ms or "0") + "000")[:3]
    return timedelta(hours=int(h), minutes=int(m), seconds=int(sec), milliseconds=int(ms))


# ============================================================
# 공통 검증  (validate_common.py)
# ============================================================

def validate_length(
    sentence: str,
    max_length: int = 18,
    weight_kor: float = 1.0,
    weight_etc: float = 1.0,
    **kwargs
) -> bool:
    """
    문장 길이 검증 (가중치 적용 가능)
    - 스타일 태그(예: {\\an8})는 글자 수에서 제외
    
    Args:
        sentence: 검증할 문장
        max_length: 최대 길이
        weight_kor: 한글 가중치
        weight_etc: 기타 문자 가중치
    
    Returns:
        True: 길이 초과 (오류)
        False: 정상
    """
    sentence = strip_style_tags(sentence)

    if weight_kor == 1.0 and weight_etc == 1.0:
        return len(sentence) > max_length

    total_length = 0
    for ch in sentence:
        if "가" <= ch <= "힣":
            total_length += weight_kor
        else:
            total_length += weight_etc
    return total_length > max_length

def validate_byte_length(sentence: str, max_length: int = 36, **kwargs) -> bool:
    """
    길이 기반 바이트 검증
    - 스타일 태그(예: {\\an8})는 바이트 수에서 제외
    
    Args:
        sentence: 검증할 문장
        max_length: 최대 바이트 길이
    
    Returns:
        True: 바이트 길이 초과 (오류)
        False: 정상
    """
    sentence = strip_style_tags(sentence)
    return max_length < len(sentence.encode("utf-8"))

def validate_length_lines(
    content: str,
    max_length: int = 18,
    valid_type: str = "length",
    weight_kor: float = 1.0,
    weight_etc: float = 1.0,
    **kwargs
) -> bool:
    """
    줄별 길이 검증
    
    Args:
        content: 자막 내용 (여러 줄 가능)
        max_length: 최대 길이
        valid_type: "length" 또는 "byte"
        weight_kor: 한글 가중치
        weight_etc: 기타 문자 가중치
    
    Returns:
        True: 길이 초과하는 줄이 있음 (오류)
        False: 모든 줄이 정상
    """
    
    list_content = content.split("\n")
    for sentence in list_content:
        if valid_type == "length":
            if validate_length(sentence, max_length, weight_kor, weight_etc):
                return True
        elif valid_type == "byte":
            if validate_byte_length(sentence):
                return True
    return False

def validate_line_count(content: str, max_lines: int = 2, **kwargs) -> bool:
    """
    자막 줄 수 검증
    
    Args:
        content: 자막 내용
        max_lines: 최대 줄 수
    
    Returns:
        True: 줄 수 초과 (오류)
        False: 정상
    """
    return max_lines <= content.count("\n")

def validate_pair_characters(
    content: str,
    pair_char: Optional[Dict[str, str]] = None,
    **kwargs
) -> bool:
    """
    괄호/따옴표/음표 짝 검증
    
    Args:
        content: 자막 내용
        pair_char: 짝을 이루는 문자 딕셔너리
    
    Returns:
        True: 짝이 맞지 않음 (오류)
        False: 정상
    """
    if not content:
        return False

    if pair_char is None:
        pair_char = {
            "(": ")",
            "[": "]",
            # '"': '"',
            # "'": "'",
            "<": ">",
            "♪": "♪",
        }

    s = content.replace("\n", " ")

    # 1) 대칭(열=닫) 문자: 개수가 홀수면 오류
    for ch, close in pair_char.items():
        if ch == close:
            if s.count(ch) % 2 == 1:
                return True

    # 2) 비대칭(열!=닫) 문자: 스택으로 검증
    open_to_close = {o: c for o, c in pair_char.items() if o != c}
    close_to_open = {c: o for o, c in open_to_close.items()}

    stack: List[str] = []
    for ch in s:
        if ch in open_to_close:
            stack.append(ch)
            continue
        if ch in close_to_open:
            if not stack:
                return True
            top = stack.pop()
            if open_to_close[top] != ch:
                return True

    return len(stack) != 0

def validate_special_characters_allow_music_note(content: str, **kwargs) -> bool:
    """
    사용 불가 특수 문자 검증 (♫는 허용)
    - True  → 오류 있음
    - False → 정상
    """

    content = content.replace("\n", " ")
    content = content.replace("’", "'").replace("‘", "'") #?

    punctuation_without_slash = string.punctuation.replace("/", "")

    ansi_chars = (
        "".join(chr(i) for i in range(0xAC00, 0xD7A4))
        + string.ascii_letters
        + string.digits
        + punctuation_without_slash
        + " "
    )

    allowed_extra = "♪"

    # 1) 기본 특수문자 / 미허용 문자 / '/' 검증
    for char in content:
        if char in allowed_extra:
            continue
        if char not in ansi_chars:
            return True
        if char == "/":
            return True

    return False

def validate_empty_content(content: str, **kwargs) -> bool:
    """
    빈 싱크 검증
    
    Args:
        content: 자막 내용
    
    Returns:
        True: 내용이 비어있음 (오류)
        False: 정상
    """
    return False if content.strip() else True

def validate_sync_negative_or_zero(start_time: timedelta, end_time: timedelta, **kwargs) -> bool:
    """
    싱크 시간이 마이너스 혹은 0인지 확인
    
    Args:
        start_time: 시작 시간
        end_time: 종료 시간
    
    Returns:
        True: 시작 시간 >= 종료 시간 (오류)
        False: 정상
    """
    return True if start_time >= end_time else False

def validate_ellipsis_count(content: str, criterion: int = 5, **kwargs) -> bool:
    """
    말줄임표의 마침표 개수 검증

    2개는 1개로, 3~4개는 3개로 후처리(postprocess_normalize_ellipsis)되므로
    후처리로 정리할 수 없는 개수만 재작업 대상으로 잡는다.

    Args:
        content: 자막 내용
        criterion: 오류로 판단할 최소 마침표 개수 (기본값: 5)

    Returns:
        True: 마침표가 criterion 개 이상 연속됨 (오류)
        False: 정상
    """
    content = content.replace("\n", " ")
    matches = re.findall(r"\.{2,}", content)
    for m in matches:
        if len(m) >= criterion:
            return True
    return False


# ============================================================
# 공통 후처리 (1차 · 2차 공용)  (postprocess_common.py)
# ============================================================

def postprocess_strip_whitespace(sentence: str, **kwargs) -> str:
    """
    문장 앞뒤 공백 제거
    
    Args:
        sentence: 처리할 텍스트
    
    Returns:
        공백이 제거된 텍스트
    """
    return sentence.strip()

def postprocess_normalize_spaces(sentence: str, **kwargs) -> str:
    """
    연속된 공백을 단일 공백으로 정규화
    
    Args:
        sentence: 처리할 텍스트
    
    Returns:
        공백이 정규화된 텍스트
    """
    return re.sub(r"[^\S\r\n]{2,}", " ", sentence)

def postprocess_normalize_wrong_mixed_punctuations(sentence: Optional[str], **kwargs) -> str:
    """
    잘못된 특수문자/구두점/오탈자 표기를 정규화
    - 잘못된 마침표(．) → .
    - 잘못된 작은따옴표(') → '
    - 가운뎃점(·) → .
    - 큰따옴표(", “, ”, ＂ 등) → 삭제
    - 오탈자 정규화

    Args:
        text: 처리할 텍스트

    Returns:
        정규화된 텍스트
    """
    if sentence is None:
        return ""
    return (
        sentence.replace("‘", "'")
        .replace("’", "'")
        .replace("．", ".")
        .replace('"', "")
        .replace("“", "")
        .replace("”", "")
        .replace("＂", "")
        .replace("·", ".")
        .replace("곘", "겠")
        .replace("꼐", "께")

    )

def postprocess_add_space_after_special_punctuation(sentence: str, **kwargs) -> str:
    """
    ... ? ! 뒤에 바로 글자가 오면 공백 1칸 추가 (맨 앞은 제외)
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        공백이 추가된 텍스트
    """
    if sentence is None:
        return ""

    def _repl(m: re.Match) -> str:
        if m.start(1) == 0:
            return m.group(1) + m.group(2)
        return f"{m.group(1)} {m.group(2)}"

    # ... ? ! 패턴
    pattern1 = re.compile(r'(\.{3,}|[?!])([가-힣A-Za-z0-9])')
    
    # ~ 패턴 (범위 표현 제외: 숫자~숫자는 유지)
    pattern2 = re.compile(r'(?<!\d)(~)([가-힣A-Za-z0-9])')  # 숫자는 제외

    lines = sentence.splitlines()
    out_lines = []

    for line in lines:
        # ... ? ! 처리
        new_line = pattern1.sub(_repl, line)
        # ~ 처리 (한글/영문만)
        new_line = pattern2.sub(_repl, new_line)
        
        out_lines.append(new_line)

    return "\n".join(out_lines)

def postprocess_trim_speaker_spaces(sentence: str, **kwargs) -> str:
    """
    괄호 안쪽 공백 제거
    
    Args:
        sentence: 처리할 문장
    
    Returns:
        괄호 안쪽 공백이 제거된 문장
    """
    sentence = re.sub(r"\(\s+", "(", sentence)
    sentence = re.sub(r"\s+\)", ")", sentence)
    sentence = re.sub(r"\[\s+", "[", sentence)
    sentence = re.sub(r"\s+\]", "]", sentence)
    return sentence

def postprocess_add_speaker_space(sentence: str, **kwargs) -> str:
    """
    화자 표시 닫는 괄호 뒤 공백 추가
    
    Args:
        sentence: 처리할 텍스트
    
    Returns:
        공백이 추가된 텍스트
    """
    return re.sub(r"\)([^\s\[\(])", r") \1", sentence)

def postprocess_normalize_ellipsis(sentence: str, **kwargs) -> str:
    """
    말줄임표 정규화

    - 2개 → 1개
    - 3개 → 3개 (유지)
    - 4개 → 3개
    - 5개 이상 → 그대로 유지 (validate_ellipsis_count가 재작업 대상으로 잡는다)

    Args:
        sentence: 처리할 문장

    Returns:
        말줄임표가 정규화된 문장
    """
    def _replace_dots(match):
        dots = match.group(0)
        count = len(dots)
        if count == 2:
            return "."
        if count in (3, 4):
            return "..."
        return dots

    result = re.sub(r"\.{2,}", _replace_dots, sentence)
    result = re.sub(r"\s+$", "", result)
    return result

def postprocess_remove_wrong_punctuation(sentence: str, **kwargs) -> str:
    """
    - 문장 앞의 . ... ? ! ~ 제거
    - 문장 끝 쉼표 , 삭제
    - '..'(2개 연속)은 위치 무관하게 유지

    Args:
        sentence: 처리할 텍스트

    Returns:
        잘못된 구두점이 제거된 텍스트
    """
    if sentence is None:
        return ""

    lines = sentence.splitlines()
    out = []

    for line in lines:
        line_text = line
        kept = []

        def _keep(m):
            kept.append(m.group(0))
            return f"\uE000{len(kept) - 1}\uE001"

        # '..' 보호
        line_text = re.sub(r"\.\.", _keep, line_text)

        # 문장 앞 잘못된 구두점 제거
        line_text = re.sub(r"^[\.\?\!~]+\s*", "", line_text)

        # 보호 토큰 복원
        line_text = re.sub(
            r"\uE000(\d+)\uE001",
            lambda m: kept[int(m.group(1))],
            line_text,
        )
        out.append(line_text)

    # 전체 자막 끝(마지막 줄 끝)의 쉼표만 삭제
    if out:
        out[-1] = re.sub(r",\s*$", "", out[-1])

    return "\n".join(out)

def postprocess_normalize_repeats(sentence: Optional[str], **kwargs) -> str:
    """
    같은 특수기호 반복을 1개로 축약하되, 점(.) 계열은 건드리지 않음.
    포함: ! ? , ~
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        중복 기호가 제거된 텍스트
    """
    if sentence is None:
        return ""
    normalized_text = sentence
    normalized_text = re.sub(r"([!?,~])\1+", r"\1", normalized_text)
    return normalized_text

def postprocess_normalize_mix_characters(
    sentence: Optional[str],
    pattern: str = r"[!?.,~]+",
    **kwargs,
) -> str:
    """
    혼합 특수기호 런 정규화.

    규칙:
    - 마침표만으로 이루어진 런은 postprocess_normalize_ellipsis에 위임
      (2개→1개, 3~4개→3개, 5개 이상은 유지하여 검증 대상으로 남김)
    - 마침표가 섞인 연속 문장부호 안에 마침표가 2개 이상 포함되면 '...'으로 치환
      예: '..!', '..!.', '.!...', '...!!', '...!' → '...'
    - 그 외 연속 문장부호는 마지막 부호만 남김
      예: '?!' → '!', ',.' → '.', '!!!??' → '?'
    """
    if sentence is None:
        return ""

    def _collapse_run(m: re.Match) -> str:
        run = m.group(0)

        # 마침표만인 런은 말줄임표 규칙이 단일 기준을 갖도록 위임한다
        if set(run) == {"."}:
            return postprocess_normalize_ellipsis(run)

        # 마침표가 2개 이상 섞여 있으면 말줄임표로 치환
        if run.count(".") >= 2:
            return "..."

        # 그 외에는 연속 부호 삭제 규칙 적용: 마지막 부호만 남김
        return run[-1]

    return re.sub(pattern, _collapse_run, sentence)

def postprocess_sync_overlap(
    front_end_time: timedelta,
    back_start_time: timedelta,
    **kwargs
):
    """
    앞 종료==뒤 시작이면 앞 종료를 10ms 당김
    
    Args:
        front_end_time: 앞 자막 종료 시간
        back_start_time: 뒤 자막 시작 시간
    
    Returns:
        조정된 앞 자막 종료 시간
    """
    if front_end_time == back_start_time:
        adjusted = front_end_time - timedelta(milliseconds=10)
        if adjusted < timedelta(0):
            adjusted = timedelta(0)
        return adjusted
    return front_end_time

def postprocess_reset_subtitles_from_list(
    subtitles: List[srt.Subtitle],
    **kwargs
) -> List[srt.Subtitle]:
    """
    리스트 기반 인덱스 재부여 + 시간 순 정렬
    
    Args:
        subtitles: 자막 리스트
    
    Returns:
        정렬되고 인덱스가 재부여된 자막 리스트
    """
    if not subtitles:
        return []
    subtitles_sorted = sorted(subtitles, key=lambda s: s.start)
    for i, sub in enumerate(subtitles_sorted, start=1):
        sub.index = i
    return subtitles_sorted

def postprocess_fix_yae_yee(sentence: str, **kwargs) -> str:
    """
    한글 보정: 중성이 ㅒ/ㅖ + 종성이 ㅆ인 글자를 ㅐ/ㅔ로 변환
    - 중성 ㅒ + 종성 ㅆ → 중성 ㅐ + 종성 ㅆ (예: 핬 → 했)
    - 중성 ㅖ + 종성 ㅆ → 중성 ㅔ + 종성 ㅆ (예: 걨 → 겠)
    - NFD(분해형, macOS 등) 한글도 NFC(조합형)로 정규화 후 처리

    한글 유니코드 분해 원리:
        한글 = 0xAC00 + (초성 × 21 × 28) + (중성 × 28) + 종성
        - 중성 ㅐ = 1, ㅒ = 3
        - 중성 ㅔ = 5, ㅖ = 7
        - 종성 ㅆ = 20

    예시:
    - "핬어요"  → "했어요"
    - "걨다"    → "겠다"
    - "갰다"    → "갰다"  (중성이 ㅐ이므로 변환 안 함)
    - "안녕"    → "안녕"  (조건 미해당)

    Args:
        sentence: 처리할 문장

    Returns:
        보정된 문장
    """
    if not sentence:
        return sentence

    # NFD(분해형, macOS 등) 한글을 NFC(조합형)로 정규화
    sentence = unicodedata.normalize("NFC", sentence)

    HANGUL_BASE = 0xAC00
    HANGUL_END = 0xD7A3

    # 중성 인덱스
    JUNG_YAE = 3   # ㅒ
    JUNG_YEE = 7   # ㅖ
    JUNG_AE = 1    # ㅐ
    JUNG_E = 5     # ㅔ

    # 종성 인덱스
    JONG_SSANG_SIOT = 20  # ㅆ

    NUM_JUNG = 21
    NUM_JONG = 28

    out = []
    for ch in sentence:
        code = ord(ch)

        # 한글 음절 범위가 아니면 그대로
        if not (HANGUL_BASE <= code <= HANGUL_END):
            out.append(ch)
            continue

        # 한글 분해
        syllable_index = code - HANGUL_BASE
        cho = syllable_index // (NUM_JUNG * NUM_JONG)
        jung = (syllable_index % (NUM_JUNG * NUM_JONG)) // NUM_JONG
        jong = syllable_index % NUM_JONG

        # 조건: 종성이 ㅆ이고 중성이 ㅒ 또는 ㅖ
        if jong == JONG_SSANG_SIOT and jung in (JUNG_YAE, JUNG_YEE):
            new_jung = JUNG_AE if jung == JUNG_YAE else JUNG_E
            new_code = HANGUL_BASE + cho * NUM_JUNG * NUM_JONG + new_jung * NUM_JONG + jong
            out.append(chr(new_code))
        else:
            out.append(ch)

    return "".join(out)

def postprocess_fix_position_tag(sentence: str, **kwargs) -> str:
    """
    위치 태그 오타 보정: 다양한 입력 실수를 정상 형태 {\an8}로 보정

    * 현재 위치 태그는 {\an8}만 사용
    * 일반 텍스트와 혼동되지 않도록 안전한 케이스만 보정

    처리 대상:
    1) 중괄호 + 백슬래시(또는 슬래시) 모두 있는 경우
       - {\무8}, {\무8, {\AN8}, {\AN8, {\an8 등
       - {/an8}, { \an 8 } 등 변형도 처리
       - 닫는 중괄호는 있거나 없거나 OK
    2) 중괄호로 감싸진 한글/영문 변형 (닫는 중괄호 필수)
       - {무8}, {an8}, {AN8} 등 → {\an8} (백슬래시 누락 보정)
       - 백슬래시(\)가 제어 문자(BEL=\x07 등)로 깨진 경우도 처리
         예: {\an8} 입력 시 \a가 BEL로 변환되어 {[BEL]n8}로 저장된 경우
       - 닫는 중괄호 없으면 일반 텍스트일 수 있으므로 보정 안 함

    제외 (일반 텍스트와 혼동 위험):
    - 양쪽 중괄호 누락 (\an8, \무8, an8 등)
    - 닫는 중괄호 누락

    예시:
    - "{\무8}안녕"      → "{\an8}안녕"
    - "{\AN8 안녕"      → "{\an8}안녕"
    - "{/an8}안녕"      → "{\an8}안녕"
    - "{무8}안녕"       → "{\an8}안녕"
    - "{an8}안녕"       → "{\an8}안녕"
    - "{[BEL]n8}안녕"   → "{\an8}안녕"  (BEL은 \a가 깨진 형태)
    - "{무8 안녕"       → "{무8 안녕" (변화 없음, 안전)
    - "\an8 안녕"       → "\an8 안녕" (변화 없음, 안전)
    - "an8 데이터"      → "an8 데이터" (변화 없음, 안전)

    Args:
        sentence: 처리할 문장

    Returns:
        보정된 문장
    """
    if not sentence:
        return sentence

    # 1단계: 중괄호 + 백슬래시(또는 슬래시) 모두 있는 경우 (가장 명확)
    # 매칭 예: {\무8}, {\무8, {\AN8}, {\AN8, {\an8, {/an8}, { \an 8 } 등
    pattern1 = re.compile(
        r"\{\s*[\\/]+\s*(?:무|an)\s*8\s*\}?",
        re.IGNORECASE
    )
    sentence = pattern1.sub(r"{\\an8}", sentence)

    # 2단계: 중괄호로 감싸진 한글/영문 변형 (닫는 중괄호 필수)
    # 매칭 예: {무8}, {an8}, {AN8} → {\an8}
    # - 백슬래시(\)가 제어 문자(BEL 등)로 깨진 경우도 함께 처리
    # - "a" 자체가 BEL로 변환되어 사라진 경우도 처리 (a?로 a를 선택적으로)
    pattern2 = re.compile(
        r"\{[\x00-\x1F\s]*(?:무|a?n)\s*8\s*\}",
        re.IGNORECASE
    )
    sentence = pattern2.sub(r"{\\an8}", sentence)

    return sentence

def postprocess_normalize_comma_space(sentence: Optional[str], **kwargs) -> str:
    """
    쉼표 앞뒤 공백 정규화

    규칙:
    - 천 단위 구분 쉼표(뒤에 숫자 정확히 3개, 예: 1,000)는 앞뒤 공백 없이 유지
      공백이 끼어 있으면 삭제 ("2, 400" -> "2,400")
    - 숫자 나열(예: "1, 2, 3")은 천 단위가 아니므로 일반 규칙 적용
    - 자막 맨 끝 쉼표는 그대로 유지 -> 따로 삭제 하는 함수 있음
    - 쉼표 앞 일반 공백/탭은 삭제
    - 쉼표 뒤 일반 공백/탭은 공백 1칸으로 정규화
    - 쉼표 뒤 공백이 없으면 공백 1칸 추가
    - 쉼표 뒤 줄바꿈은 공백으로 간주하여 그대로 유지

    예시:
    - "안녕,반가워"   → "안녕, 반가워"
    - "안녕, 반가워"  → "안녕, 반가워"
    - "안녕 ,반가워"  → "안녕, 반가워"
    - "안녕 , 반가워" → "안녕, 반가워"
    - "안녕,\n반가워" → "안녕,\n반가워"
    - "1,000원"      → "1,000원"
    - "2, 400억"     → "2,400억"   (천 단위)
    - "1, 2, 3"      → "1, 2, 3"   (나열이므로 뒤 공백 유지)
    - "10, 20"       → "10, 20"    (뒤 숫자가 2개)
    - "안녕,"        → "안녕,"
    - ",안녕"        → ", 안녕"
    - ", 안녕"       → ", 안녕"

    Args:
        sentence: 처리할 문장

    Returns:
        쉼표 공백이 정규화된 문장
    """
    if sentence is None:
        return ""

    out = []
    i = 0
    n = len(sentence)

    while i < n:
        char = sentence[i]

        if char != ",":
            out.append(char)
            i += 1
            continue

        # 천 단위 구분 쉼표는 앞뒤 공백 없이 유지 (예: 1,000)
        # 공백이 끼어 있어도 붙여준다 (예: "2, 400" / "2 ,400" / "2 , 400" -> "2,400")
        #
        # 판정: 앞이 숫자이고 뒤에 숫자가 '정확히 3개' 오는 경우만 천 단위로 본다.
        # "1, 2, 3" / "10, 20" 처럼 숫자를 나열하는 경우와 구분하기 위한 것으로,
        # 나열은 일반 규칙(앞 공백 삭제 + 뒤 공백 1칸)을 그대로 적용한다.
        p = i - 1
        while p >= 0 and sentence[p] in (" ", "\t"):
            p -= 1
        q = i + 1
        while q < n and sentence[q] in (" ", "\t"):
            q += 1

        prev_is_digit = p >= 0 and sentence[p].isdigit()
        next_is_thousands = (
            q + 2 < n
            and sentence[q:q + 3].isdigit()
            and not (q + 3 < n and sentence[q + 3].isdigit())
        )

        if prev_is_digit and next_is_thousands:
            while out and out[-1] in (" ", "\t"):
                out.pop()
            out.append(char)
            i = q
            continue

        # 자막 맨 끝 쉼표는 그대로 유지
        if i == n - 1:
            out.append(char)
            i += 1
            continue

        # 쉼표 앞 일반 공백/탭 삭제
        # 줄바꿈은 자막 줄 구조이므로 삭제하지 않음
        while out and out[-1] in (" ", "\t"):
            out.pop()

        out.append(",")

        next_char = sentence[i + 1]

        # 쉼표 뒤 줄바꿈은 공백으로 간주하여 그대로 유지
        if next_char in ("\n", "\r"):
            i += 1
            continue

        # 쉼표 뒤 일반 공백/탭은 공백 1칸으로 정규화
        if next_char in (" ", "\t"):
            j = i + 1

            while j < n and sentence[j] in (" ", "\t"):
                j += 1

            # 공백 뒤에 줄바꿈이 오면 공백을 추가하지 않고 줄바꿈 유지
            if j < n and sentence[j] not in ("\n", "\r"):
                out.append(" ")

            i = j
            continue

        # 쉼표 뒤 공백이 없으면 공백 1칸 추가
        out.append(" ")
        i += 1

    return "".join(out)

def postprocess_normalize_period_space(sentence: Optional[str], **kwargs) -> str:
    """
    마침표 앞뒤 공백 정규화

    규칙:
    - 마침표 앞 일반 공백/탭은 삭제
    - 마침표 뒤에 글자(한글/영문/숫자)가 이어지면 공백 1칸으로 정규화
    - 마침표 뒤에 글자가 없으면(문장 끝/줄바꿈/닫는 괄호·부호) 공백을 추가하지 않음
    - 숫자 사이 마침표(예: 6.25)는 앞뒤 공백 없이 유지하며,
      공백이 끼어 있으면 삭제
    - 연속 마침표(말줄임표)는 건드리지 않음
      (postprocess_normalize_ellipsis / add_space_after_special_punctuation 담당)

    예시:
    - "안녕 .세요"   → "안녕. 세요"
    - "안녕.세요"    → "안녕. 세요"
    - "안녕 . 세요"  → "안녕. 세요"
    - "안녕하세요."  → "안녕하세요."
    - "안녕.\n세요"  → "안녕.\n세요"
    - "6.25 전쟁"    → "6.25 전쟁"
    - "6. 25 전쟁"   → "6.25 전쟁"
    - "6 .25 전쟁"   → "6.25 전쟁"
    - "아니..."      → "아니..."
    - "(대사입니다.)" → "(대사입니다.)"

    Args:
        sentence: 처리할 문장

    Returns:
        마침표 공백이 정규화된 문장
    """
    if sentence is None:
        return ""

    out = []
    i = 0
    n = len(sentence)

    while i < n:
        char = sentence[i]

        if char != ".":
            out.append(char)
            i += 1
            continue

        # 연속 마침표(말줄임표)는 통째로 통과시킨다
        run_end = i
        while run_end < n and sentence[run_end] == ".":
            run_end += 1

        if run_end - i > 1:
            out.append(sentence[i:run_end])
            i = run_end
            continue

        # 공백을 건너뛴 앞뒤 문자로 숫자 사이 여부 판정
        p = i - 1
        while p >= 0 and sentence[p] in (" ", "\t"):
            p -= 1
        q = i + 1
        while q < n and sentence[q] in (" ", "\t"):
            q += 1

        prev_is_digit = p >= 0 and sentence[p].isdigit()
        next_is_digit = q < n and sentence[q].isdigit()

        # 마침표 앞 일반 공백/탭 삭제 (줄바꿈은 줄 구조이므로 보존)
        while out and out[-1] in (" ", "\t"):
            out.pop()

        out.append(".")

        # 숫자 사이 마침표는 뒤 공백도 삭제
        if prev_is_digit and next_is_digit:
            i = q
            continue

        next_char = sentence[i + 1] if i + 1 < n else ""

        # 뒤에 글자가 이어지지 않으면 공백을 추가하지 않음
        if not next_char or next_char in ("\n", "\r"):
            i += 1
            continue

        # 마침표 뒤 일반 공백/탭은 공백 1칸으로 정규화
        if next_char in (" ", "\t"):
            if q < n and sentence[q] not in ("\n", "\r"):
                out.append(" ")

            i = q
            continue

        # 마침표 뒤 공백이 없으면, 글자가 이어질 때만 공백 1칸 추가
        # (닫는 괄호나 다른 문장부호 앞에는 붙이지 않는다)
        if next_char.isalnum():
            out.append(" ")

        i += 1

    return "".join(out)

def postprocess_remove_delete_tag(
    subs: List[srt.Subtitle],
    **kwargs
) -> List[srt.Subtitle]:
    """
    편집자 스타일 마커 처리

    처리 규칙:
    1. {\ㅅ} 마커 (전체 삭제 신호):
       - 괄호 () 안에 있으면 → 괄호를 포함한 전체 그룹 삭제
         예: "(해설{\ㅅ}) 안녕" → " 안녕"
       - 괄호 밖에 있으면 → 해당 자막 전체 삭제 (텍스트 + 시간)
         예: "안녕{\ㅅ}" → 자막 리스트에서 제거

    2. {\} 마커 (부분 삭제):
       - 문장 어디든 {\}가 있으면 삭제
       - {\} 뒤에 마침표(.)가 이어지면 마침표도 함께 삭제
       - 앞은 건드리지 않음
         예: "네.{\}"      → "네."
         예: "안녕.{\}."   → "안녕."
         예: "안녕.{\}..." → "안녕."

    처리 순서: {\ㅅ} 먼저 → {\}

    예시:
    - "(해설{\ㅅ}) 저랑 데이트..."  → " 저랑 데이트..."
    - "너야?{\ㅅ}"                → (자막 삭제)
    - "네.{\}"                    → "네."
    - "안녕.{\}."                 → "안녕."
    - "안녕.{\}..."               → "안녕."

    Args:
        subs: 자막 리스트

    Returns:
        처리된 자막 리스트 ({\ㅅ}이 괄호 밖에 있는 자막은 리스트에서 제외됨)
    """
    if not subs:
        return subs

    result: List[srt.Subtitle] = []

    for sub in subs:
        content = sub.content

        if not content:
            result.append(sub)
            continue

        # 1단계: (내용{\ㅅ}) 형태 → 괄호 전체 삭제
        # 괄호 안에 {\ㅅ}이 포함된 경우만 매칭
        content = re.sub(r"\([^()]*\{\\ㅅ\}[^()]*\)", "", content)

        # 2단계: 남아있는 {\ㅅ}이 있으면 (괄호 밖) → 자막 전체 삭제
        if "{\\ㅅ}" in content:
            continue  # 이 자막은 결과에 추가하지 않음

        # 3단계: {\} 처리 (뒤 마침표도 함께 삭제)
        content = re.sub(r"\{\\\}\.*", "", content)

        # content 업데이트
        sub.content = content
        result.append(sub)

    return result

def postprocess_remove_empty_subs(
    subs: List[srt.Subtitle],
    **kwargs
) -> List[srt.Subtitle]:
    """
    빈 자막 제거

    - content가 None 또는 빈 문자열이거나, 공백/줄바꿈만 있는 자막을 리스트에서 제거
    - 다른 후처리 함수에서 자막 내용이 모두 삭제되어 빈 싱크가 생긴 경우 정리 목적

    예시:
    - content = "" → 삭제
    - content = None → 삭제
    - content = "   " (공백만) → 삭제
    - content = "\n\n" (줄바꿈만) → 삭제
    - content = "안녕" → 유지

    Args:
        subs: 자막 리스트

    Returns:
        빈 자막이 제거된 리스트
    """
    if not subs:
        return subs

    return [sub for sub in subs if sub.content and sub.content.strip()]


# ============================================================
# 2차 후처리  (postprocess_stage2.py)
# ============================================================

def postprocess_merge_overlapped_sync(subs: List[srt.Subtitle], max_lines_per_sub: int = 1, **kwargs) -> List[srt.Subtitle]:
    """
    오버랩 자막 병합
    - '맞닿음(앞.end == 뒤.start)'은 처리하지 않음
    - '겹침(앞.end > 뒤.start)'만 병합
    - 두 자막 모두 텍스트가 max_lines_per_sub 줄 이하일 때만 병합
    
    Args:
        subs: 자막 리스트
        max_lines_per_sub: 병합 가능한 자막당 최대 줄 수 (기본 1)
            - 2개 자막 병합 시: 각 자막의 줄 수 상한 (예: 1이면 1줄+1줄 → 2줄 병합)
            - 3개 이상 반복 병합 시: postprocess_mark_overlapped_multi_speaker에서
              max_merged_lines 값을 이 파라미터로 전달하여 병합 결과물의 총 줄 수를 제어
              (예: max_merged_lines=3이면 2줄+1줄 → 3줄 병합 허용)
    
    Returns:
        병합된 자막 리스트
    """
    if not subs:
        return subs

    def _within_max_lines(text: str) -> bool:
        if text is None:
            return False
        return text.strip().count("\n") < max_lines_per_sub

    subs = sorted(subs, key=lambda x: (x.start, x.end))
    result: List[srt.Subtitle] = []
    i = 0
    n = len(subs)

    while i < n:
        cur = subs[i]
        if i == n - 1:
            result.append(cur)
            break

        nxt = subs[i + 1]

        if (cur.end > nxt.start) and _within_max_lines(cur.content) and _within_max_lines(nxt.content):
            merged = srt.Subtitle(
                index=cur.index,
                start=cur.start,
                end=max(cur.end, nxt.end),
                content=f"{cur.content}\n{nxt.content}",
            )
            set_origin_indices(
                merged,
                get_origin_indices(cur) + get_origin_indices(nxt)
            )
            result.append(merged)
            i += 2
        else:
            result.append(cur)
            i += 1

    # return srt.sort_and_reindex(result)
    # (이식) from utils… import postprocess_reset_subtitles_from_list — 이 모듈에 이미 정의되어 있음
    return postprocess_reset_subtitles_from_list(result)

def postprocess_convert_characters(
    text: Optional[str],
    from_chars: str = "[]",
    to_chars: str = "()",
    **kwargs
) -> str:
    """
    기호 변경 (예: [] → ())
    
    Args:
        text: 처리할 텍스트
        from_chars: 변경할 문자들
        to_chars: 변경될 문자들
    
    Returns:
        변경된 텍스트
    """
    if text is None:
        return ""

    if len(from_chars) == len(to_chars):
        table = str.maketrans(from_chars, to_chars)
        return text.translate(table)

    if len(to_chars) == 1:
        table = str.maketrans({ch: to_chars for ch in from_chars})
        return text.translate(table)

    if len(from_chars) == 1:
        return text.replace(from_chars, to_chars)

    return text

# NOTE: postprocess_sync_overlap — postprocess_common.py 판을 덮어씀 (mediaflow import 순서와 동일)

def postprocess_sync_overlap(
    front_end_time: timedelta,
    back_start_time: timedelta,
    **kwargs
) -> timedelta:
    """
    싱크 맞닿음 조정
    앞 종료==뒤 시작이면 앞 종료를 10ms 당김
    
    Args:
        front_end_time: 앞 자막 종료 시간
        back_start_time: 뒤 자막 시작 시간
    
    Returns:
        조정된 앞 자막 종료 시간
    """
    if front_end_time == back_start_time:
        adjusted = front_end_time - timedelta(milliseconds=10)
        if adjusted < timedelta(0):
            adjusted = timedelta(0)
        return adjusted
    return front_end_time

def postprocess_remove_last_punctuation(
    sentence: str,
    punctuation: List[str] = None,
    **kwargs
) -> str:
    """
    마지막 구두점 제거
    - 각 라인의 맨 끝 '단일' 구두점만 제거 (기본 '.')
    - 말줄임표 '...' 는 보존
    
    Args:
        sentence: 처리할 문장
        punctuation: 제거할 구두점 리스트
    
    Returns:
        구두점이 제거된 문장
    """
    if sentence is None:
        return ""
    
    if punctuation is None:
        punctuation = ["."]

    lines = sentence.splitlines()
    out = []

    for line in lines:
        raw = line
        s = raw.rstrip()

        if not s:
            out.append(raw)
            continue

        if s.endswith("..."):
            out.append(raw)
            continue

        if s[-1] in punctuation:
            s = s[:-1]

        out.append(s)

    return "\n".join(out)

def postprocess_remove_not_pair_characters(
    content: str,
    pair_char: Optional[Dict[str, str]] = None,
    **kwargs
) -> str:
    """
    한쌍이 아니면 삭제 (괄호/따옴표/기호)
    
    Args:
        content: 처리할 내용
        pair_char: 짝을 이루는 문자 딕셔너리
    
    Returns:
        짝이 맞지 않는 문자가 제거된 텍스트
    """
    if content is None:
        return ""
    
    if pair_char is None:
        pair_char = {
            "(": ")",
            "[": "]",
            '"': '"',
            "'": "'",
            "<": ">",
            "♪": "♪",
        }

    flat = replace_linebreak(content)
    text = content

    for open_char, close_char in pair_char.items():
        open_count = flat.count(open_char)
        close_count = flat.count(close_char)

        if open_char == close_char:
            if open_count % 2 != 0:
                text = text.replace(open_char, "")
            continue

        if open_count != close_count:
            text = text.replace(open_char, "")
            text = text.replace(close_char, "")

    return text

def postprocess_remove_mid_period(sentence: str, **kwargs) -> str:
    """
    문장 중간 마침표 제거 (소수/말줄임표/'..' 제외)
    - '..'(2개 연속)은 위치 무관하게 유지

    Args:
        sentence: 처리할 텍스트

    Returns:
        중간 마침표가 제거된 텍스트
    """
    if sentence is None:
        return ""

    lines = sentence.splitlines()
    out = []

    for line in lines:
        line_text = line
        kept = []

        def _keep(m):
            kept.append(m.group(0))
            return f"\uE000{len(kept) - 1}\uE001"

        # 1) 말줄임표(3개 이상) 보호
        line_text = re.sub(r"\.{3,}", _keep, line_text)

        # 2) '..'(2개 연속) 보호 — 위치 무관
        line_text = re.sub(r"\.\.", _keep, line_text)

        # 3) 소수 제외한 중간 마침표 제거
        line_text = re.sub(r"(?<!\d)\.(?!\d)(?!\s*$)", "", line_text)

        # 4) 보호 토큰 복원
        line_text = re.sub(
            r"\uE000(\d+)\uE001",
            lambda m: kept[int(m.group(1))],
            line_text,
        )
        out.append(line_text)

    return "\n".join(out)

def _split_line_half(line: str) -> str:
    """절반 기준 가장 가까운 공백에서 줄 바꿈. 공백 없으면 절반 강제."""
    mid = len(line) // 2
    # 절반 기준 가장 가까운 공백 찾기
    best = -1
    best_dist = len(line)
    for idx, ch in enumerate(line):
        if ch == " ":
            dist = abs(idx - mid)
            if dist < best_dist:
                best_dist = dist
                best = idx
    if best >= 0:
        return line[:best] + "\n" + line[best + 1:]
    else:
        return line[:mid] + "\n" + line[mid:]

def postprocess_add_period_between_subs(
    subs: List[srt.Subtitle],
    ending_punctuation: str = ".!?~",
    max_chars_per_line: int = 17,
    max_lines: int = 3,
    **kwargs
) -> List[srt.Subtitle]:
    """
    자막 간 마침표 삽입 + 글자 수 초과 시 줄 바꿈
    - 앞 자막의 마지막 줄 끝에 문장부호(.!?~...)가 없고
      뒷 자막의 첫 줄이 하이픈(-) 혹은 (으로 시작하면
      앞 자막 마지막 줄 끝에 마침표(.) 삽입
    - 마침표 추가 후 글자 수 초과 시, 줄 수 여유가 있으면 줄 바꿈

    Args:
        subs: 자막 리스트
        ending_punctuation: 문장부호 문자열 (기본 ".!?~")
        max_chars_per_line: 한 줄 최대 글자 수
        max_lines: 자막 최대 줄 수

    Returns:
        처리된 자막 리스트
    """
    if not subs:
        return subs

    for i in range(len(subs) - 1):
        cur = subs[i]
        nxt = subs[i + 1]

        if not cur.content or not nxt.content:
            continue

        nxt_first_line = nxt.content.splitlines()[0].strip()
        if not (nxt_first_line.startswith("-") or nxt_first_line.startswith("(")):
            continue

        cur_lines = cur.content.splitlines()
        last_line = cur_lines[-1].rstrip()

        if not last_line:
            continue

        if last_line.endswith("..."):
            continue

        if last_line[-1] in ending_punctuation:
            continue

        if last_line[-1] in ")]":
            continue

        # 마침표 삽입
        cur_lines[-1] = last_line + "."

        # 글자 수 초과 시 줄 바꿈 시도
        if len(strip_style_tags(cur_lines[-1])) > max_chars_per_line:
            if len(cur_lines) < max_lines:
                split_result = _split_line_half(cur_lines[-1])
                cur_lines[-1] = split_result

        cur.content = "\n".join(cur_lines)

    return subs

def postprocess_add_period_between_lines(
    sentence: str,
    ending_punctuation: str = ".!?~",
    max_chars_per_line: int = 17,
    max_lines: int = 3,
    **kwargs
) -> str:
    """
    줄 간 마침표 삽입 + 글자 수 초과 시 줄 바꿈
    - 앞 줄 끝에 문장부호(.!?~...)가 없고
      뒷 줄이 하이픈(-) 혹은 (으로 시작하면
      앞 줄 끝에 마침표(.) 삽입
    - 마침표 추가 후 글자 수 초과 시, 줄 수 여유가 있으면 줄 바꿈

    Args:
        sentence: 처리할 문장
        ending_punctuation: 문장부호 문자열 (기본 ".!?~")
        max_chars_per_line: 한 줄 최대 글자 수
        max_lines: 자막 최대 줄 수

    Returns:
        마침표가 삽입된 문장
    """
    if sentence is None:
        return ""

    lines = sentence.splitlines()

    if len(lines) < 2:
        return sentence

    for i in range(len(lines) - 1):
        cur_line = lines[i].rstrip()
        nxt_line = lines[i + 1].strip()

        if not cur_line or not nxt_line:
            continue

        if not (nxt_line.startswith("-") or nxt_line.startswith("(")):
            continue

        if cur_line.endswith("..."):
            continue

        if cur_line[-1] in ending_punctuation:
            continue

        if cur_line[-1] in ")]":
            continue

        # 마침표 삽입
        cur_line = cur_line + "."

        # 글자 수 초과 시 줄 바꿈 시도
        if len(strip_style_tags(cur_line)) > max_chars_per_line:
            if len(lines) < max_lines:
                split_result = _split_line_half(cur_line)
                # 줄 바꿈으로 1줄이 2줄이 되므로 리스트에 삽입
                split_parts = split_result.split("\n")
                lines[i] = split_parts[0]
                lines.insert(i + 1, split_parts[1])
                # 삽입으로 인덱스 밀림 — 하지만 이미 마침표 처리 완료된 줄이므로 OK
            else:
                lines[i] = cur_line
        else:
            lines[i] = cur_line

    return "\n".join(lines)

def postprocess_remove_oc_check(text: str, **kwargs) -> str:
    """^ 제거"""
    if text is None:
        return ""
    return re.sub(r"\^", "", text)

def postprocess_remove_double_quotation_mark(text: str, **kwargs) -> str:
    """큰따옴표 제거"""
    if text is None:
        return ""
    return re.sub(r'"', "", text)

def postprocess_remove_star(text: str, **kwargs) -> str:
    """별표 제거"""
    if text is None:
        return ""
    return re.sub(r"\*", "", text)

def postprocess_remove_music_notes(text: str, **kwargs) -> str:
    """음표 제거"""
    if text is None:
        return ""
    return re.sub(r"[♪♫]", "", text)

def postprocess_remove_square_brackets(text: str, **kwargs) -> str:
    """대괄호 제거"""
    if text is None:
        return ""
    return re.sub(r"[\[\]]", "", text)

def postprocess_remove_parentheses(text: str, **kwargs) -> str:
    """소괄호 제거"""
    if text is None:
        return ""
    return re.sub(r"[\(\)]", "", text)

def postprocess_remove_angle_brackets(text: str, **kwargs) -> str:
    """꺾쇠 제거"""
    if text is None:
        return ""
    return re.sub(r"[<>]", "", text)

def postprocess_remove_other_characters(text: str, **kwargs) -> str:
    """
    JTBC 전용: 통합 기호 제거
    - *, ♪, ♫, [], (), <>, ^
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        기호가 제거된 텍스트
    """
    if text is None:
        return ""

    out = text
    out = postprocess_remove_star(out)
    out = postprocess_remove_music_notes(out)
    out = postprocess_remove_square_brackets(out)
    out = postprocess_remove_parentheses(out)
    out = postprocess_remove_angle_brackets(out)
    out = postprocess_remove_oc_check(out)
    return out

def postprocess_normalize_asterisk_for_skbb(sentence: str, **kwargs) -> str:
    """
    SKBB 전용: 별표 정규화
    - 별표가 2개 이상 반복되면 '**' 로 통일
    - 1개면 'asterisks' 라는 토큰으로 치환
    
    Args:
        sentence: 처리할 문장
    
    Returns:
        별표가 정규화된 문장
    """
    def replace_asterisks(match):
        asterisks = match.group(0)
        count = len(asterisks)
        if count > 2:
            return "**"
        if count == 2:
            return "**"
        return "asterisks"

    result = re.sub(r"\*{2,}", replace_asterisks, sentence)
    result = re.sub(r"\s+$", "", result)
    return result

def postprocess_remove_star_and_angle_for_skbb(text: str, **kwargs) -> str:
    """
    SKBB 전용: 미허용 기호 제거
    - 큰따옴표, 음표, 소괄호, 별표, 꺾쇠를 제거하는 통합 후처리
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        기호가 제거된 텍스트
    """
    if text is None:
        return ""

    t = text
    t = postprocess_remove_double_quotation_mark(t)
    t = postprocess_remove_music_notes(t)
    t = postprocess_remove_parentheses(t)
    # t = postprocess_remove_star(t)
    t = postprocess_remove_angle_brackets(t)
    return t

def postprocess_remove_not_pair_paren_quotes_for_skbb(text: str, **kwargs) -> str:
    """
    SKBB 전용: 짝 안 맞는 작은따옴표('), 꺾쇠(< >)만 제거
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        짝이 맞지 않는 문자가 제거된 텍스트
    """
    if text is None:
        return ""
    return postprocess_remove_not_pair_characters(
        text,
        pair_char={
            "'": "'",
            "<": ">",
        },
    )

def postprocess_remove_first_hypn(
    sentence: str,
    punctuation: Optional[str] = None,
    **kwargs
) -> str:

    # 내용이 없으면 그대로
    if not sentence:
        return sentence

    subtitle_index = kwargs.get('subtitle_index', None)

    # 첫 번째 자막이 아니면 아무 것도 하지 않음
    if subtitle_index is None or subtitle_index != 1:
        return sentence

    if punctuation is None:
        punctuation = "-"

    # 선행 공백 있으면 스킵 후 첫 글자가 하이픈이면 제거
    i = 0
    n = len(sentence)
    while i < n and sentence[i].isspace():
        i += 1

    if i < n and sentence[i] in punctuation:
        return sentence[:i] + sentence[i + 1 :]
    return sentence

def postprocess_keep_bracket_music_note_and_remove_others_for_lghv(text: str, **kwargs) -> str:
    """
    LGHV 전용: [♫ ...]만 살리고 나머지 음표 제거
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        처리된 텍스트
    """
    if text is None:
        return ""

    SENTINEL = "\uE000"
    out = text
    out = re.sub(r"\[♫\s*", "[♫ ", out)
    out = out.replace("[♫ ", f"[{SENTINEL} ")
    out = re.sub(r"[♫]", "", out)
    out = out.replace(f"[{SENTINEL} ", "[♫ ")
    return out

def postprocess_remove_star_and_angle_for_lghv(text: str, **kwargs) -> str:
    """
    LGHV 전용: 별표와 꺾쇠 제거
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        기호가 제거된 텍스트
    """
    if text is None:
        return ""
    out = text
    out = postprocess_remove_star(out)
    out = postprocess_remove_angle_brackets(out)
    return out

def postprocess_remove_not_pair_paren_quotes_for_lghv(text: str, **kwargs) -> str:
    """
    LGHV 전용: 짝이 맞지 않는 괄호/따옴표 제거
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        짝이 맞지 않는 문자가 제거된 텍스트
    """
    if text is None:
        return ""
    pair_char = {
        "(": ")",
        '"': '"',
        "'": "'",
    }
    return postprocess_remove_not_pair_characters(text, pair_char=pair_char)

def postprocess_normalize_music_to_double_note_for_lghv(text: str, **kwargs) -> str:
    """
    LGHV 전용: 음표 통일 (♫로)
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        음표가 정규화된 텍스트
    """
    if text is None:
        return ""
    return re.sub(r"[♩♪♫♬♭♮♯]", "♫", text)

def postprocess_normalize_music_to_single_note_for_tvng(text: str, **kwargs) -> str:
    """
    TVING 전용: 음표 통일 (♪로)
    
    Args:
        text: 처리할 텍스트
    
    Returns:
        음표가 정규화된 텍스트
    """
    if text is None:
        return ""
    return re.sub(r"[♩♪♫♬♭♮♯]", "♪", text)

def postprocess_apply_overlap_hyphen_for_all_speech(
    subs: List[srt.Subtitle],
    dash_prefix: str = "- ",
    **kwargs
) -> List[srt.Subtitle]:
    """
    다화자 오버랩 표기

    규칙:
    - 오버랩 그룹에서 발화 싱크가 2개 이상 존재하고,
      허용 오버랩 총 줄 수 조건을 만족하면 그룹 내 모든 발화 싱크에 "- " 표기를 붙인다.
    - 허용 총 줄 수:
        * 음향 포함이면 <= 3줄
        * 음향 미포함이면 <= 2줄
    - 음향 싱크에는 붙이지 않는다.
    - 이미 "- "로 시작하면 중복 삽입하지 않는다.

    Args:
        subs: 자막 리스트
        dash_prefix: 발화 앞에 붙일 접두사

    Returns:
        처리된 자막 리스트
    """
    if not subs:
        return subs

    ordered = sorted(subs, key=lambda x: (x.start, x.end, x.index))

    def _non_empty_lines_count(content: str) -> int:
        return sum(
            1
            for line in (content or "").splitlines()
            if line.strip()
        )

    def _is_sound_event_content(content: str) -> bool:
        lines = [
            line.strip()
            for line in (content or "").splitlines()
            if line.strip()
        ]

        def _is_sound_line(line: str) -> bool:
            if not (line.startswith("[") and line.endswith("]")):
                return False
            return line not in ("[영어]", "[일본어]", "[중국어]", "[외국어]")

        return bool(lines) and all(_is_sound_line(line) for line in lines)

    def _is_speech_sub(sub: srt.Subtitle) -> bool:
        return not _is_sound_event_content(sub.content or "")

    def _add_dash_to_each_line_preserve_indent(content: str) -> str:
        lines = (content or "").splitlines()
        out_lines = []

        for line in lines:
            if not line.strip():
                out_lines.append(line)
                continue

            match = re.match(r"^(\s*)(.*)$", line)
            indent = match.group(1)
            core = match.group(2)

            if core.startswith(dash_prefix):
                out_lines.append(line)
            else:
                out_lines.append(f"{indent}{dash_prefix}{core}")

        return "\n".join(out_lines)

    out: List[srt.Subtitle] = []
    n = len(ordered)
    i = 0

    while i < n:
        group = [ordered[i]]
        group_end = ordered[i].end
        j = i + 1

        while j < n:
            cur = ordered[j]

            if cur.start < group_end:
                group.append(cur)
                group_end = max(group_end, cur.end)
                j += 1
            else:
                break

        if len(group) <= 1:
            out.extend(group)
            i = j
            continue

        sound_present = any(not _is_speech_sub(sub) for sub in group)
        total_lines = sum(
            _non_empty_lines_count(sub.content or "")
            for sub in group
        )
        speech_sub_count = sum(
            1
            for sub in group
            if _is_speech_sub(sub)
        )

        limit = 3 if sound_present else 2
        allowed = total_lines <= limit and speech_sub_count >= 2

        if not allowed:
            out.extend(group)
            i = j
            continue

        for sub in group:
            if not _is_speech_sub(sub):
                out.append(sub)
                continue

            new_sub = srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=_add_dash_to_each_line_preserve_indent(sub.content or ""),
                proprietary=sub.proprietary,
            )
            set_origin_indices(new_sub, get_origin_indices(sub))
            out.append(new_sub)

        i = j

    return sorted(out, key=lambda x: (x.start, x.end, x.index))

def postprocess_over_length_lines_middle(text: str, max_length: int = 18, **kwargs) -> str:
    """
    max_length 기준 줄바꿈
    - 한 줄이 max_length를 초과하면 중간에 가장 가까운 공백에서 줄바꿈
    - 스타일 태그(예: {\\an8})는 글자 수에서 제외
    - 나눈 줄도 max_length를 초과하면 반복해서 줄바꿈
    - 공백이 없으면 더 이상 나누지 않고 그대로 둠

    Args:
        text: 처리할 텍스트
        max_length: 최대 길이 (기본 18)

    Returns:
        줄바꿈이 적용된 텍스트
    """
    if text is None:
        return ""

    out_lines: List[str] = []

    for line in text.splitlines():
        if not line:
            out_lines.append(line)
            continue

        pending = [line]

        while pending:
            current = pending.pop(0)

            if len(strip_style_tags(current)) <= max_length:
                out_lines.append(current)
                continue

            visible_len = len(strip_style_tags(current))
            mid = visible_len // 2

            best_idx = -1
            best_dist = visible_len

            for idx, ch in enumerate(current):
                if ch != " ":
                    continue

                left_len = len(strip_style_tags(current[:idx]))
                dist = abs(left_len - mid)

                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            # 공백이 없으면 더 이상 나눌 수 없으므로 그대로 둠
            if best_idx < 0:
                out_lines.append(current)
                continue

            left = current[:best_idx].rstrip()
            right = current[best_idx + 1:].lstrip()

            # 잘못 나뉘는 경우 방지
            if not left or not right:
                out_lines.append(current)
                continue

            pending.insert(0, right)
            pending.insert(0, left)

    return "\n".join(out_lines)

def postprocess_remove_all_star(sentence: str, **kwargs) -> str:
    """
    문장 내 모든 별표(*) 제거

    - STT 자막 병합 시 부착되는 '*' 마커를 일괄 제거
    - 위치 무관하게 모든 '*' 삭제
    - 별표 앞뒤 문장은 그대로 유지

    처리 예시:
    - "*안녕하세요"          → "안녕하세요"
    - "*안녕\n*반갑습니다"    → "안녕\n반갑습니다"
    - "**안녕하세요"         → "안녕하세요"
    - "안녕*하세요"          → "안녕하세요"
    - "* 안녕하세요"         → " 안녕하세요"
    - "안녕하세요"           → "안녕하세요"

    Args:
        sentence: 처리할 문장

    Returns:
        모든 별표가 제거된 문장
    """
    if not sentence:
        return sentence

    return sentence.replace("*", "")

def postprocess_over_length_lines(text: str, max_length: int = 18, **kwargs) -> str:
    """
    18글자 기준 줄바꿈
    - 스타일 태그(예: {\\an8})는 글자 수에서 제외
    
    Args:
        text: 처리할 텍스트
        max_length: 최대 길이 (기본 18)
    
    Returns:
        줄바꿈이 적용된 텍스트
    """
    if text is None:
        return ""

    lines = text.splitlines()
    out_lines: List[str] = []

    for line in lines:
        if not line:
            out_lines.append(line)
            continue

        if len(strip_style_tags(line)) <= max_length:
            out_lines.append(line)
            continue

        words = line.split()
        current = ""
        wrapped_lines: List[str] = []

        for word in words:
            if not current:
                candidate = word
            else:
                candidate = current + " " + word

            if len(strip_style_tags(candidate)) > max_length and current:
                wrapped_lines.append(current)
                current = word
            else:
                current = candidate

        if current:
            wrapped_lines.append(current)

        out_lines.extend(wrapped_lines)

    return "\n".join(out_lines)

def postprocess_mark_overlapped_multi_speaker(
    subs: List[srt.Subtitle],
    reassign_index: bool = True,
    multi_speaker_prefix: str = "- ",
    max_lines_per_sub: int = 1,
    multi_overlap_strategy: str = "best_pair",
    max_merged_lines: int = 2,
    **kwargs
) -> List[srt.Subtitle]:
    """
    오버랩 다화자 구간 처리 (복잡한 로직)
    
    - 겹치는 싱크가 2개: 두 싱크 모두 하이픈(- ) 추가 후 병합
    - 겹치는 싱크가 3개 이상:
        - multi_overlap_strategy="best_pair": 가장 많이 겹치는 2개만 병합 (LGHV, JTBC)
        - multi_overlap_strategy="merge_all": 총 줄 수가 max_merged_lines 이하이면
          싱크 순서대로 전체 병합, 초과 시 병합 없이 그대로 유지 (DLIV)
    - 브라켓 태그([...])가 있으면 병합 제외 (merge_all 전략 시 제외하지 않음)
    
    Args:
        subs: 자막 리스트
        reassign_index: 인덱스 재부여 여부
        multi_speaker_prefix: 다화자 구분 접두사 (기본 "- ", 빈 문자열이면 접두사 없음)
        max_lines_per_sub: 병합 가능한 자막당 최대 줄 수 (기본 1)
        multi_overlap_strategy: 3개 이상 겹침 시 병합 전략 ("best_pair" | "merge_all")
        max_merged_lines: merge_all 전략 시 병합 결과물의 최대 허용 줄 수 (기본 2)
    
    Returns:
        처리된 자막 리스트
    """
    if not subs:
        return subs

    def _within_max_lines(text: str) -> bool:
        """텍스트가 max_lines_per_sub 줄 이하인지 여부 판별"""
        if text is None:
            return False
        return text.strip().count("\n") < max_lines_per_sub

    def _dash(line: str) -> str:
        """문장 앞에 multi_speaker_prefix를 붙이되, 이미 해당 접두사로 시작하면 그대로 둔다."""
        if line is None:
            return ""
        stripped = line.strip()
        if not multi_speaker_prefix:
            return stripped
        if stripped.startswith(multi_speaker_prefix):
            return stripped
        return f"{multi_speaker_prefix}{stripped}"

    def _is_bracket_single_line(text: str) -> bool:
        """
        1줄 텍스트가 전체가 대괄호로 감싸진 태그 형태인지 여부.
        예: "[음향효과]", "[ ♫ 노래효과 ]" → True
        """
        if text is None:
            return False
        stripped = text.strip()
        return stripped.startswith("[") and stripped.endswith("]") and len(stripped) > 2

    # 시간 순서 정렬
    ordered_subs = sorted(subs, key=lambda x: (x.start, x.end))
    first_sub_index = ordered_subs[0].index if ordered_subs else None

    result: List[srt.Subtitle] = []
    n = len(ordered_subs)
    i = 0
    no_merge_indices = set()

    # 1차: 그룹별 기본 가공
    while i < n:
        group = [ordered_subs[i]]
        group_end = ordered_subs[i].end
        j = i + 1

        while j < n:
            cur = ordered_subs[j]
            if cur.start < group_end:
                group.append(cur)
                if cur.end > group_end:
                    group_end = cur.end
                j += 1
            else:
                break

        if len(group) == 1:
            result.append(group[0])
        else:
            has_bracket_single = any(
                _within_max_lines(sub.content) and _is_bracket_single_line(sub.content)
                for sub in group
            )

            if has_bracket_single and multi_overlap_strategy != "merge_all":
                for sub in group:
                    no_merge_indices.add(sub.index)
                result.extend(group)
            else:
                if not all(_within_max_lines(sub.content) for sub in group):
                    result.extend(group)
                else:
                    if len(group) == 2:
                        g0, g1 = group
                        # new0 = srt.Subtitle(
                        #     index=g0.index,
                        #     start=g0.start,
                        #     end=g0.end,
                        #     content=_dash(g0.content) if g0.index != first_sub_index else g0.content,
                        # )
                        # new1 = srt.Subtitle(
                        #     index=g1.index,
                        #     start=g1.start,
                        #     end=g1.end,
                        #     content=_dash(g1.content) if g1.index != first_sub_index else g1.content,
                        # )
                        new0 = srt.Subtitle(
                            index=g0.index,
                            start=g0.start,
                            end=g0.end,
                            content=_dash(g0.content) if g0.index != first_sub_index else g0.content,
                        )
                        set_origin_indices(new0, get_origin_indices(g0))

                        new1 = srt.Subtitle(
                            index=g1.index,
                            start=g1.start,
                            end=g1.end,
                            content=_dash(g1.content) if g1.index != first_sub_index else g1.content,
                        )
                        set_origin_indices(new1, get_origin_indices(g1))
                        result.extend([new0, new1])
                    else:
                        result.extend(group)

        i = j

    # 2차: 병합 단계
    merge_candidates = [sub for sub in result if sub.index not in no_merge_indices]
    non_merge_subs = [sub for sub in result if sub.index in no_merge_indices]
    merge_candidates = sorted(merge_candidates, key=lambda x: (x.start, x.end, x.index))

    merged_groups: List[srt.Subtitle] = []
    m = len(merge_candidates)
    k = 0

    while k < m:
        g = [merge_candidates[k]]
        g_end = merge_candidates[k].end
        t = k + 1
        while t < m:
            cur = merge_candidates[t]
            if cur.start < g_end:
                g.append(cur)
                if cur.end > g_end:
                    g_end = cur.end
                t += 1
            else:
                break

        # if len(g) <= 2:
        #     merged_groups.extend(postprocess_merge_overlapped_sync(g, max_lines_per_sub=max_lines_per_sub))
        if len(g) <= 2:
            total_lines = sum(
                sub.content.strip().count("\n") + 1
                for sub in g if sub.content
            )
            if total_lines <= max_merged_lines:
                merged_groups.extend(postprocess_merge_overlapped_sync(g, max_lines_per_sub=max_lines_per_sub))
            else:
                merged_groups.extend(g)
        
        else:
            # --- 전체 병합 조건 ---
            total_lines = sum(
                sub.content.strip().count("\n") + 1
                for sub in g if sub.content
            )
            all_within_max = all(_within_max_lines(sub.content) for sub in g)

            if multi_overlap_strategy == "merge_all":
                if all_within_max and total_lines <= max_merged_lines:
                    g_dashed = []
                    for sub in g:
                        if sub.index == first_sub_index:
                            new_content = sub.content
                        else:
                            new_content = _dash(sub.content)
                        new_sub = srt.Subtitle(
                            index=sub.index,
                            start=sub.start,
                            end=sub.end,
                            content=new_content,
                        )
                        set_origin_indices(new_sub, get_origin_indices(sub))
                        g_dashed.append(new_sub)

                    # 싱크 순서대로 반복 병합
                    merged_result = g_dashed
                    while True:
                        prev_len = len(merged_result)
                        merged_result = postprocess_merge_overlapped_sync(
                            merged_result, max_lines_per_sub=max_merged_lines
                        )
                        if len(merged_result) >= prev_len:
                            break

                    merged_groups.extend(merged_result)
                else:
                    # merge_all 전략: 전체 병합 불가 시 병합 없이 그대로 유지
                    merged_groups.extend(g)
            else:
                best_pair: Optional[tuple] = None
                best_overlap = timedelta(0)

                for a in range(len(g)):
                    for b in range(a + 1, len(g)):
                        s1, s2 = g[a], g[b]
                        start = max(s1.start, s2.start)
                        end = min(s1.end, s2.end)
                        overlap = end - start
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_pair = (a, b)

                if best_pair is None or best_overlap <= timedelta(0):
                    merged_groups.extend(g)
                else:
                    i1, i2 = best_pair
                    if i1 > i2:
                        i1, i2 = i2, i1

                    g_with_dash: List[srt.Subtitle] = []
                    for idx_in_group, sub in enumerate(g):
                        if idx_in_group in (i1, i2):
                            if sub.index == first_sub_index:
                                new_content = sub.content
                            else:
                                new_content = _dash(sub.content)
                            # new_sub = srt.Subtitle(
                            #     index=sub.index,
                            #     start=sub.start,
                            #     end=sub.end,
                            #     content=new_content,
                            # )
                            new_sub = srt.Subtitle(
                                index=sub.index,
                                start=sub.start,
                                end=sub.end,
                                content=new_content,
                            )
                            set_origin_indices(new_sub, get_origin_indices(sub))
                            g_with_dash.append(new_sub)
                        else:
                            g_with_dash.append(sub)

                    pair = [g_with_dash[i1], g_with_dash[i2]]
                    merged_pair_list = postprocess_merge_overlapped_sync(pair, max_lines_per_sub=max_lines_per_sub)

                    group_out: List[srt.Subtitle] = []

                    if len(merged_pair_list) == 1:
                        merged_sub = merged_pair_list[0]
                        other_subs: List[srt.Subtitle] = [
                            sub for idx_in_group, sub in enumerate(g_with_dash)
                            if idx_in_group not in (i1, i2)
                        ]

                        for idx_other, other in enumerate(other_subs):
                            if not _within_max_lines(other.content):
                                continue

                            overlap_start = max(merged_sub.start, other.start)
                            overlap_end = min(merged_sub.end, other.end)

                            if overlap_end <= overlap_start:
                                continue

                            half = (overlap_end - overlap_start) / 2
                            mid = overlap_start + half

                            if merged_sub.start <= other.start:
                                # new_merged = srt.Subtitle(
                                #     index=merged_sub.index,
                                #     start=merged_sub.start,
                                #     end=mid,
                                #     content=merged_sub.content,
                                # )
                                # new_other = srt.Subtitle(
                                #     index=other.index,
                                #     start=mid,
                                #     end=other.end,
                                #     content=other.content,
                                # )
                                new_merged = srt.Subtitle(
                                    index=merged_sub.index,
                                    start=merged_sub.start,
                                    end=mid,
                                    content=merged_sub.content,
                                )
                                set_origin_indices(new_merged, get_origin_indices(merged_sub))

                                new_other = srt.Subtitle(
                                    index=other.index,
                                    start=mid,
                                    end=other.end,
                                    content=other.content,
                                )
                                set_origin_indices(new_other, get_origin_indices(other))
                            else:
                                # new_other = srt.Subtitle(
                                #     index=other.index,
                                #     start=other.start,
                                #     end=mid,
                                #     content=other.content,
                                # )
                                # new_merged = srt.Subtitle(
                                #     index=merged_sub.index,
                                #     start=mid,
                                #     end=merged_sub.end,
                                #     content=merged_sub.content,
                                # )
                                new_other = srt.Subtitle(
                                    index=other.index,
                                    start=other.start,
                                    end=mid,
                                    content=other.content,
                                )
                                set_origin_indices(new_other, get_origin_indices(other))

                                new_merged = srt.Subtitle(
                                    index=merged_sub.index,
                                    start=mid,
                                    end=merged_sub.end,
                                    content=merged_sub.content,
                                )
                                set_origin_indices(new_merged, get_origin_indices(merged_sub))

                            merged_sub = new_merged
                            other_subs[idx_other] = new_other
                            break

                        group_out.extend(other_subs)
                        group_out.append(merged_sub)
                    else:
                        group_out.extend(g_with_dash)

                    group_out_sorted = sorted(
                        group_out,
                        key=lambda x: (x.start, x.end, x.index),
                    )
                    merged_groups.extend(group_out_sorted)

        k = t

    final_subs = sorted(
        merged_groups + non_merge_subs,
        key=lambda x: (x.start, x.end, x.index),
    )

    # 맞닿음 10ms 당김 처리
    if final_subs:
        for i in range(len(final_subs) - 1):
            a = final_subs[i]
            b = final_subs[i + 1]
            a.end = postprocess_sync_overlap(a.end, b.start)

    # 인덱스 재부여
    if reassign_index:
        # (이식) from utils… import postprocess_reset_subtitles_from_list — 이 모듈에 이미 정의되어 있음
        return postprocess_reset_subtitles_from_list(final_subs)

    return final_subs

def postprocess_adjust_short_sync(
    subs: List[srt.Subtitle],
    min_duration_sec: float = 1.0,
    gap_sec: float = 0.083,
    **kwargs
) -> List[srt.Subtitle]:
    """
    1초 미만 자막 길이 연장 처리

    규칙:
    - 1초 미만 자막을 찾는다.
    - 1초까지 늘려도 다음 자막과의 간격(gap_sec) 이상을 유지할 수 있으면
      1초 지점으로 연장한다.
    - 유지할 수 없으면 최소 간격(gap_sec)을 보장하는 최대 지점까지만 연장한다.
      (결과적으로 1초 미만으로 남을 수 있음)
    - 마지막 자막은 다음 자막이 없으므로 1초까지 연장한다.

    Args:
        subs: 자막 리스트
        min_duration_sec: 최소 자막 길이 (기본 1.0초)
        gap_sec: 다음 자막과의 최소 간격 (초, 기본 0.083)

    Returns:
        후처리된 자막 리스트
    """
    if not subs:
        return subs

    min_gap = timedelta(seconds=gap_sec)
    min_dur = timedelta(seconds=min_duration_sec)
    processed_subs = sorted(list(subs), key=lambda x: (x.start, x.end))

    extended_full_count = 0
    extended_partial_count = 0

    for i, sub in enumerate(processed_subs):
        duration = sub.end - sub.start
        if duration >= min_dur:
            continue

        target_end = sub.start + min_dur
        next_sub = processed_subs[i + 1] if i < len(processed_subs) - 1 else None

        # 마지막 자막 → 1초 연장
        if next_sub is None:
            old_end = sub.end
            sub.end = target_end
            extended_full_count += 1
            logger.info(
                f"[SHORT_SYNC] 마지막 자막 1초 연장: "
                f"idx={sub.index}, {old_end} -> {sub.end}"
            )
            continue

        max_end = next_sub.start - min_gap

        if target_end <= max_end:
            # 1초 연장해도 최소 간격 유지 가능
            old_end = sub.end
            sub.end = target_end
            extended_full_count += 1
            logger.info(
                f"[SHORT_SYNC] 1초 연장: "
                f"idx={sub.index}, {old_end} -> {sub.end}"
            )
        elif max_end > sub.end:
            # 1초는 불가하지만 현재보다 늘릴 수 있음
            old_end = sub.end
            sub.end = max_end
            extended_partial_count += 1
            logger.info(
                f"[SHORT_SYNC] 부분 연장: "
                f"idx={sub.index}, {old_end} -> {sub.end}"
            )
        # else: 이미 최소 간격 경계이므로 연장 불가

    logger.info(
        f"[SHORT_SYNC] 처리 완료 - "
        f"1초 연장: {extended_full_count}개, "
        f"부분 연장: {extended_partial_count}개"
    )

    return processed_subs

def postprocess_merge_gap_subs(
    subs: List[srt.Subtitle],
    gap_sec: float = 0.083,
    max_lines_after_merge: int = 3,
    max_chars_per_line: int = 17,
    max_gap_sec: float = 0.4,
    multi_speaker_prefix: str = "",
    **kwargs
) -> List[srt.Subtitle]:
    """
    기본 간격(gap_sec) 자막 병합 처리 + 문장 병합

    규칙:
    0. 병합 대상 자막이 다른 자막과 오버랩 상태이면 병합 대상에서 제외
    1. 두 자막의 간격이 정확히 gap_sec인 경우 병합 시도 (아니면 시도 X)
       (A) 문장 병합 가능 시:
           - 합친 글자 수가 max_chars_per_line 초과하면 문장 병합 안 함 → (B)로
           - 이하이면 문장 병합 적용, 병합 후 줄 수 ≤ max_lines_after_merge이면 자막 병합
       (B) 문장 병합 불가 시:
           - 병합 후 줄 수 ≤ max_lines_after_merge이면 자막 병합
    2. 뒷 자막과 병합 불가 시, 간격 0.4초 이내 앞 자막과 동일 로직 시도
    3. 앞뒤 모두 불가하면 그대로 둠

    * 오버랩 판정: 병합 후보 두 자막 중 하나라도 제3의 자막과 시간이 겹쳐 있으면
      (긴 자막 안에 짧은 자막이 포함된 경우 포함) 해당 쌍은 병합하지 않음

    * 구분자(multi_speaker_prefix): 빈 문자열이면 붙이지 않음(기본).
      값이 있으면 (B) 줄 쌓기로 병합된 결과가 2줄 이상일 때 각 줄 맨 앞에 붙인다.
      (A) 문장 병합은 한 문장이 이어지는 경우이므로 붙이지 않는다.
      이미 해당 접두사로 시작하는 줄은 그대로 두어 재실행에 안전하다.

    Args:
        subs: 자막 리스트
        gap_sec: 기본 간격 (초, 기본 0.083)
        max_lines_after_merge: 병합 허용 최대 줄 수 (기본 3)
        max_chars_per_line: 한 줄 최대 글자 수 (기본 17)
        max_gap_sec: 앞 자막 병합 시도 최대 간격 (초, 기본 0.4)
        multi_speaker_prefix: 줄 쌓기 병합 시 각 줄 맨 앞에 붙일 구분자
            (기본 "" = 붙이지 않음, 예: "-")

    Returns:
        후처리된 자막 리스트
    """
    if not subs:
        return subs

    # (이식) from utils… import get_origin_indices, set_origin_indices — 이 모듈에 이미 정의되어 있음

    ending_punctuation = ".!?~"
    gap_td = timedelta(seconds=gap_sec)
    processed_subs = sorted(list(subs), key=lambda x: (x.start, x.end))

    # origin_indices 기본 세팅
    for sub in processed_subs:
        if not hasattr(sub, "_origin_indices"):
            set_origin_indices(sub, [sub.index])

    def _is_overlapping(a: srt.Subtitle, b: srt.Subtitle) -> bool:
        """두 자막이 시간적으로 겹치는지 확인"""
        return a.start < b.end and b.start < a.end

    def _has_any_overlap(idx: int) -> bool:
        """idx번 자막이 다른 어떤 자막과든 오버랩되어 있는지 확인
        (긴 자막 안에 포함된 경우도 감지하기 위해 앞쪽은 break 없이 전수 검사)
        """
        target = processed_subs[idx]
        # 앞쪽 확인 (역방향) — 긴 자막이 target을 포함할 수 있으므로 break하지 않음
        for j in range(idx - 1, -1, -1):
            if _is_overlapping(target, processed_subs[j]):
                return True
        # 뒤쪽 확인 — start 기준 정렬이므로 break 유효
        for j in range(idx + 1, len(processed_subs)):
            if processed_subs[j].start >= target.end:
                break
            if _is_overlapping(target, processed_subs[j]):
                return True
        return False

    def _can_merge_text(last_line: str, first_line: str) -> bool:
        """문장 병합 조건 확인"""
        last_line = last_line.rstrip()
        first_line = first_line.strip()

        if not last_line or not first_line:
            return False
        if last_line.endswith("..."):
            return False
        if last_line[-1] in ending_punctuation:
            return False
        if first_line.startswith("-") or first_line.startswith("("):
            return False
        if last_line[-1] in ")":
            return False
        return True

    def _dash(line: str) -> str:
        """줄 맨 앞에 multi_speaker_prefix를 붙이되, 이미 붙어 있으면 그대로 둔다."""
        stripped = line.strip()
        if not stripped or stripped.startswith(multi_speaker_prefix):
            return stripped
        return f"{multi_speaker_prefix}{stripped}"

    def _apply_prefix(content: str) -> str:
        """줄 쌓기 병합 결과(2줄 이상)의 각 줄에 구분자 부착"""
        if not multi_speaker_prefix:
            return content
        lines = content.splitlines()
        if len(lines) < 2:
            return content
        return "\n".join(_dash(line) for line in lines)

    def _try_merge_subs(front: srt.Subtitle, back: srt.Subtitle) -> bool:
        """
        front(앞)과 back(뒤) 자막의 병합을 시도한다.
        문장 병합 가능하면 문장 병합 적용 후 자막 병합.
        문장 병합 불가하면 줄 수만 체크하여 자막 병합.
        Returns: True if merged
        """
        front_lines = front.content.splitlines() if front.content else []
        back_lines = back.content.splitlines() if back.content else []

        if not front_lines or not back_lines:
            return False

        front_line_count = len(front_lines)
        back_line_count = len(back_lines)

        # 문장 병합 시도
        last_line = front_lines[-1]
        first_line = back_lines[0]

        if _can_merge_text(last_line, first_line):
            merged_line = last_line.rstrip() + " " + first_line.strip()
            if len(strip_style_tags(merged_line)) <= max_chars_per_line:
                # 문장 병합 적용 시 줄 수: 문장 병합으로 1줄 감소
                total_lines = front_line_count + back_line_count - 1
                if total_lines <= max_lines_after_merge:
                    front_lines[-1] = merged_line
                    remaining_back = back_lines[1:]

                    if remaining_back:
                        merged_content = "\n".join(front_lines) + "\n" + "\n".join(remaining_back)
                    else:
                        merged_content = "\n".join(front_lines)

                    front.content = merged_content
                    front.end = max(front.end, back.end)
                    set_origin_indices(
                        front,
                        get_origin_indices(front) + get_origin_indices(back)
                    )
                    return True

        # 문장 병합 불가 (또는 글자 수 초과) → 줄 수만 체크하여 자막 병합
        total_lines = front_line_count + back_line_count
        if total_lines <= max_lines_after_merge:
            front_content = front.content.strip() if front.content else ""
            back_content = back.content.strip() if back.content else ""

            if front_content and back_content:
                merged_content = f"{front_content}\n{back_content}"
            elif front_content:
                merged_content = front_content
            else:
                merged_content = back_content

            # 별개 문장을 줄로 쌓은 결과이므로 화자 구분자 부착 (설정 시)
            merged_content = _apply_prefix(merged_content)

            front.content = merged_content
            front.end = max(front.end, back.end)
            set_origin_indices(
                front,
                get_origin_indices(front) + get_origin_indices(back)
            )
            return True

        return False

    merged_count = 0
    i = 0

    while i < len(processed_subs):
        # 마지막 자막은 뒤 자막이 없으므로 종료
        if i >= len(processed_subs) - 1:
            break

        cur = processed_subs[i]
        nxt = processed_subs[i + 1]
        actual_gap = nxt.start - cur.end

        # 1) 처음 대상은 "정확히 gap_sec" 인 경우만
        if actual_gap != gap_td:
            i += 1
            continue

        # 0) 병합 대상이 다른 자막과 오버랩 상태면 병합 대상에서 제외
        if _has_any_overlap(i) or _has_any_overlap(i + 1):
            i += 1
            continue

        # 2) 뒤 자막과 병합 시도
        if _try_merge_subs(cur, nxt):
            processed_subs.pop(i + 1)
            merged_count += 1
            logger.info(
                f"[MERGE_GAP] 뒷 자막과 병합: "
                f"idx={cur.index}+{nxt.index}"
            )
            # 같은 위치에서 재검사 (연쇄 병합 가능)
            continue

        # 3) 뒤 자막과 병합 불가 시에만 앞 자막과 시도
        if i > 0:
            prev = processed_subs[i - 1]
            prev_gap = (cur.start - prev.end).total_seconds()

            if prev_gap <= max_gap_sec:
                # 앞 자막도 오버랩 체크
                if _has_any_overlap(i - 1) or _has_any_overlap(i):
                    i += 1
                    continue

                if _try_merge_subs(prev, cur):
                    processed_subs.pop(i)
                    merged_count += 1
                    logger.info(
                        f"[MERGE_GAP] 앞 자막과 병합: "
                        f"idx={prev.index}+{cur.index}"
                    )
                    # cur가 삭제되었으므로 이전 위치부터 다시 검사
                    i = max(i - 1, 0)
                    continue

        # 앞뒤 모두 병합 불가 → 그대로 유지
        i += 1

    # 재인덱싱
    for new_index, sub in enumerate(processed_subs, start=1):
        sub.index = new_index

    logger.info(f"[MERGE_GAP] 처리 완료 - 병합: {merged_count}개")

    return processed_subs

def postprocess_adjust_subtitle_gaps(
    subs: List[srt.Subtitle],
    gap_sec: float = 0.083,
    **kwargs
) -> List[srt.Subtitle]:
    """
    자막 간격 조정
    - 각 자막 사이의 간격이 0 이상이고 gap_sec 미만이면,
      앞 자막의 end 시간을 next.start - gap_sec 로 조정
    - 오버랩 그룹이 있는 경우, 그룹 내 가장 늦은 end 기준으로
      다음 자막과의 간격을 판단하여 조정
    - 그 외에는 건드리지 않음

    Args:
        subs: 자막 리스트
        gap_sec: 최소 간격 (초, 기본 0.083)

    Returns:
        간격 조정된 자막 리스트
    """
    if not subs:
        return subs

    # (이식) from utils… import get_origin_indices, set_origin_indices — 이 모듈에 이미 정의되어 있음
    # (이식) from utils… import postprocess_reset_subtitles_from_list — 이 모듈에 이미 정의되어 있음

    min_gap = timedelta(seconds=gap_sec)
    zero_gap = timedelta(0)
    subs = sorted(subs, key=lambda x: (x.start, x.end))

    result: List[srt.Subtitle] = []
    # 오버랩 그룹 내 가장 늦은 end를 추적
    group_max_end = subs[0].end

    for i, cur in enumerate(subs):
        # group_max_end 갱신
        if cur.start >= group_max_end:
            # 새 그룹 시작
            group_max_end = cur.end
        else:
            # 오버랩 그룹 내 — max end 갱신
            group_max_end = max(group_max_end, cur.end)

        if i < len(subs) - 1:
            nxt = subs[i + 1]
            current_gap = nxt.start - cur.end
            effective_gap = nxt.start - group_max_end

            # 자기 자신의 gap은 오버랩이 아니고,
            # 그룹 기준 effective_gap이 0 이상 ~ min_gap 미만이면 조정
            if zero_gap <= current_gap and zero_gap <= effective_gap < min_gap:
                origin = get_origin_indices(cur)
                prev_end = cur.end

                cur = srt.Subtitle(
                    index=cur.index,
                    start=cur.start,
                    end=nxt.start - min_gap,
                    content=cur.content,
                    proprietary=cur.proprietary,
                )
                set_origin_indices(cur, origin)

                logger.info(f"[GAPS] idx={cur.index}, end {prev_end} -> {cur.end}")

        result.append(cur)

    return postprocess_reset_subtitles_from_list(result)

def postprocess_remove_space_after_hypn(
    sentence: str,
    **kwargs
) -> str:
    """
    맨 앞 하이픈 뒤 공백 제거
    - 각 라인의 맨 앞이 '- '(하이픈+공백)으로 시작하면
      공백을 제거하여 '-텍스트' 형태로 변환

    Args:
        sentence: 처리할 문장

    Returns:
        하이픈 뒤 공백이 제거된 문장
    """
    if sentence is None:
        return ""

    lines = sentence.splitlines()
    out = []

    for line in lines:
        stripped = line.lstrip()

        if stripped.startswith("- "):
            stripped = "-" + stripped[2:]

        out.append(stripped)

    return "\n".join(out)

def postprocess_remove_leading_hypn_no_space_for_dliv(
    sentence: str,
    **kwargs
) -> str:
    """
    한 줄 자막의 맨 앞 하이픈(뒤에 공백 없음) 제거

    - 1줄 자막의 맨 앞이 '-'이고 바로 뒤가 공백이 아니면 하이픈을 제거
      예: '-대사' -> '대사', '--대사' -> '대사'
    - '- 대사'처럼 하이픈 뒤에 공백이 있으면 그대로 둔다
    - 하이픈만 있는 라인('-')도 그대로 둔다
    - 선행 공백은 유지

    2차 오버랩 병합(postprocess_mark_overlapped_multi_speaker)이 화자 구분
    하이픈을 붙이므로, 그 전에 실행하여 하이픈이 중복 부착되는 것을 막는다.

    ※ 2줄 이상 자막은 건드리지 않는다.
      2차 후처리는 70_check_rule_v2에 파일이 들어올 때마다 실행되므로,
      70 -> 60_rework_v2 -> 70 왕복 시 재실행된다. 병합 결과물은 항상 2줄
      이상이므로, 여러 줄 자막을 제외하면 이전 회차가 부착한 화자 구분
      하이픈(및 작업자가 직접 만든 다화자 블록)이 보존된다.
      전체 줄을 대상으로 하면 왕복 2회차에 하이픈이 영구 소멸한다.

    Args:
        sentence: 처리할 문장

    Returns:
        맨 앞 하이픈이 제거된 문장
    """
    if sentence is None:
        return ""

    lines = sentence.splitlines()

    # 이미 완성된 다화자 블록이므로 보존
    if len(lines) > 1:
        return sentence

    out = [re.sub(r"^(\s*)-+(?=\S)", r"\1", line) for line in lines]

    return "\n".join(out)


# ============================================================
# 2차 검증  (validate_stage2.py)
# ============================================================

def validate_special_characters(content: str, **kwargs) -> bool:
    """
    사용할 수 없는 특수 기호 검증 (음표 미허용)
    
    Args:
        content: 자막 내용
    
    Returns:
        True: 오류 있음
        False: 정상
    """
    content = replace_linebreak(content)
    ansi_chars = (
        "".join(chr(i) for i in range(0xAC00, 0xD7A4))
        + string.ascii_letters
        + string.digits
        + string.punctuation
        + " "
    )

    for char in content:
        if char not in ansi_chars:
            return True
    return False

# NOTE: validate_special_characters_allow_music_note — validate_common.py 판을 덮어씀 (mediaflow import 순서와 동일)

def validate_special_characters_allow_music_note(content: str, **kwargs) -> bool:
    """
    사용 불가 특수 문자 검증 (♫는 허용)
    - True  → 오류 있음
    - False → 정상
    """

    content = content.replace("\n", " ")
    content = content.replace("’", "'").replace("‘", "'") #?

    punctuation_without_slash = string.punctuation.replace("/", "")

    ansi_chars = (
        "".join(chr(i) for i in range(0xAC00, 0xD7A4))
        + string.ascii_letters
        + string.digits
        + punctuation_without_slash
        + " "
    )

    allowed_extra = "♪"

    # 1) 기본 특수문자 / 미허용 문자 / '/' 검증
    for char in content:
        if char in allowed_extra:
            continue
        if char not in ansi_chars:
            return True
        if char == "/":
            return True

    return False

def validate_overlapped_over_lines(
    front_content: str,
    back_content: str,
    front_end_time: timedelta,
    back_start_time: timedelta,
    max_lines: int = 2
) -> bool:
    """
    오버랩 + n줄 검증
    오버랩된 싱크 중 텍스트 n줄이 있는지 검사
    
    Args:
        front_content: 앞 자막 내용
        back_content: 뒤 자막 내용
        front_end_time: 앞 자막 종료 시간
        back_start_time: 뒤 자막 시작 시간
    
    Returns:
        True: 오류 (n줄 이상 오버랩)
        False: 정상
    """
    if front_end_time <= back_start_time:
        return False

    def _line_count(text: str) -> int:
        if not text or not text.strip():
            return 0
        return text.count("\n") + 1

    front_lines = _line_count(front_content)
    back_lines = _line_count(back_content)

    return True if (front_lines >= max_lines or back_lines >= max_lines) else False

def validate_hyphen_no_space_after_for_skbb(content: str, **kwargs) -> bool:
    """
    SKBB 전용: 하이픈 사용 규칙 검증

    규칙:
    - 줄 시작 '-' 다음에 공백이 오면 오류
    - 그 외 정상

    Returns:
        True: 오류
        False: 정상
    """
    if not content:
        return False
    lines = content.splitlines()
    for line in lines:
        stripped_leading = line.lstrip()
        if not stripped_leading.startswith("-"):
            continue
        if len(stripped_leading) == 1:
            continue
        if stripped_leading[1].isspace():
            return True
    return False

def validate_mosaic_count_for_skbb(content: str, criterion: int = 2, **kwargs) -> bool:
    """
    SKBB 전용: 모자이크(*) 개수 검증
    
    Args:
        content: 자막 내용
        criterion: 기준 개수 (기본 2)
    
    Returns:
        True: 오류 (별표가 1개만 있음)
        False: 정상 (0개 또는 2개 이상)
    """
    if not content:
        return False

    # 연속된 '*' 그룹 추출
    star_groups = re.findall(r"\*+", content)

    # '*'가 아예 없으면 정상
    if not star_groups:
        return False

    # 그룹 단위 검증
    for group in star_groups:
        # 선행 후처리에서 모자이크를 최대 2개로 후처리한 다음 검증 진행,
        # 문장 내 그룹 중 애스터리스크 문자열 길이가 2가 아니면 오류로 반환,
        if len(group) != criterion:
            return True 

    return False

def validate_sync_overlapped(
    front_content: str,
    back_content: str,
    front_end_time: timedelta,
    back_start_time: timedelta,
    **kwargs
) -> bool:
    """
    오버랩(싱크 겹침)만 검증
    - 오버랩이 존재하면 비정상(True)
    - 오버랩이 없으면 정상(False)

    Args:
        front_end_time: 앞 자막 종료 시간
        back_start_time: 뒤 자막 시작 시간

    Returns:
        True: 오류 (오버랩 존재)
        False: 정상 (오버랩 없음)
    """
    if front_end_time is None or back_start_time is None:
        return False

    return True if front_end_time > back_start_time else False

def validate_overlapped_only_text_for_lghv(
    front_content: str,
    back_content: str,
    front_end_time: timedelta,
    back_start_time: timedelta,
    **kwargs
) -> bool:
    """
    LGHV 전용: 오버랩된 싱크들이 대사+대사인지 확인
    오버랩(겹침)인 1줄+1줄 싱크에 대해,
    둘 중 하나라도 '대괄호 태그([ ... ])만으로 구성'되어 있으면 오류
    
    Args:
        front_content: 앞 자막 내용
        back_content: 뒤 자막 내용
        front_end_time: 앞 자막 종료 시간
        back_start_time: 뒤 자막 시작 시간
    
    Returns:
        True: 오류 (대괄호 태그와 대사가 오버랩)
        False: 정상
    """
    # 겹침이 아니면 검사 대상 아님
    if front_end_time <= back_start_time:
        return False

    def _is_single_line(text: str) -> bool:
        if text is None:
            return False
        return "\n" not in text.strip()

    def _is_bracket_only_single_line(text: str) -> bool:
        """
        텍스트 전체가 대괄호로 감싸진 1줄 태그인지.
        예:
          "[음향효과]" / "[ ♫ 노래 ]" / "[SFX]"  -> True
          "대사 [음향효과]" -> False
          "[음향] 대사" -> False
        """
        if text is None:
            return False
        stripped = text.strip()
        if not stripped:
            return False
        if not (stripped.startswith("[") and stripped.endswith("]")):
            return False
        inner = stripped[1:-1].strip()
        if not inner:
            return False
        return True

    # 1줄+1줄이 아닌 경우는 여기서 판단하지 않음
    if not (_is_single_line(front_content) and _is_single_line(back_content)):
        return False

    # 둘 중 하나라도 "[...]" 단독이면 오류
    if _is_bracket_only_single_line(front_content) or _is_bracket_only_single_line(back_content):
        return True

    return False

def validate_overlapped_accumulated_lines(
    subtitles: List[srt.Subtitle],
    max_lines: int = 3,
    **kwargs
) -> Dict[int, str]:
    """
    연속 오버랩 그룹의 누적 줄 수를 검사한다.

    예)
    A(1줄), B(1줄), C(2줄)이 하나의 연속 오버랩 그룹이면
    총 4줄로 보고 max_lines 초과 시 그룹 전체를 오류 처리한다.

    Returns:
        {subtitle.index: 오류상세}
    """
    if not subtitles:
        return {}

    # (이식) from utils… import get_origin_indices — 이 모듈에 이미 정의되어 있음

    ordered = sorted(subtitles, key=lambda x: (x.start, x.end, x.index))
    errors: Dict[int, str] = {}

    def _line_count(text: str) -> int:
        if not text or not text.strip():
            return 0
        return text.count("\n") + 1

    # 수정필요파일 원본 제공 시
    # def _flush_group(group: List[srt.Subtitle]):
    #     if len(group) < 2:
    #         return

    #     total_lines = sum(_line_count(sub.content) for sub in group)
    #     if total_lines <= max_lines:
    #         return

    #     # origin_indices 수집
    #     group_origin_indices = []
    #     for sub in group:
    #         group_origin_indices.extend(get_origin_indices(sub))
    #     group_origin_indices = sorted(set(group_origin_indices))

    #     detail = (
    #         f"연속 오버랩 구간 #{', #'.join(map(str, group_origin_indices))} "
    #         f"총 {total_lines}줄 ({max_lines}줄 초과)"
    #     )

    #     for sub in group:
    #         errors[sub.index] = detail
    # 수정필요파일 후처리 이후 제공 시
    def _flush_group(group: List[srt.Subtitle]):
        if len(group) < 2:
            return

        total_lines = sum(_line_count(sub.content) for sub in group)
        if total_lines <= max_lines:
            return

        # current index 사용
        group_indices = [sub.index for sub in group]

        detail = (
            f"연속 오버랩 구간 #{', #'.join(map(str, group_indices))} "
            f"총 {total_lines}줄 ({max_lines}줄 초과)"
        )

        for sub in group:
            errors[sub.index] = detail

    current_group: List[srt.Subtitle] = []
    current_group_end = None

    for sub in ordered:
        if not current_group:
            current_group = [sub]
            current_group_end = sub.end
            continue

        if sub.start < current_group_end:
            current_group.append(sub)
            if sub.end > current_group_end:
                current_group_end = sub.end
        else:
            _flush_group(current_group)
            current_group = [sub]
            current_group_end = sub.end

    _flush_group(current_group)
    return errors

def validate_sync_gap(
    subtitles: List[srt.Subtitle],
    gap_sec: float = 0.083,
    **kwargs
) -> Dict[int, str]:
    """
    자막 간 최소 간격 검증 (안전망)

    postprocess_adjust_subtitle_gaps가 간격을 보장하므로 정상 흐름에서는
    걸리지 않는다. 후처리가 누락되거나 규칙이 변경됐을 때를 잡기 위한 검증이다.

    판정 기준은 postprocess_adjust_subtitle_gaps와 동일하게 맞춘다.
    - 오버랩 그룹의 가장 늦은 종료 시각(group_max_end)을 기준으로
      다음 자막과의 간격을 본다
    - 그 간격이 0 이상 gap_sec 미만이면 오류
    - 오버랩/포함 상태(간격이 음수)는 대상이 아니다
      (오버랩 자체는 validate_overlapped_accumulated_lines 등이 담당)

    예)
    A(0~2.0), B(2.0~4.0)        -> 간격 0초, 오류
    A(0~1.917), B(2.0~4.0)      -> 간격 0.083초, 정상
    A(0~3.0), B(1.0~2.0)        -> 포함 상태, 대상 아님
    A(0~3.0), B(1.0~2.0), C(3.0~4.0)
        -> B와 C의 간격은 1.0초지만 그룹 종료(3.0) 기준 0초이므로 오류

    Args:
        subtitles: 자막 리스트
        gap_sec: 보장해야 하는 최소 간격 (초, 기본 0.083)

    Returns:
        {subtitle.index: 오류상세}
    """
    if not subtitles:
        return {}

    zero_gap = timedelta(0)
    min_gap = timedelta(seconds=gap_sec)

    ordered = sorted(subtitles, key=lambda x: (x.start, x.end, x.index))
    errors: Dict[int, str] = {}

    # 오버랩 그룹 내 가장 늦은 end를 추적
    group_max_end = ordered[0].end

    for i, cur in enumerate(ordered):
        if cur.start >= group_max_end:
            # 새 그룹 시작
            group_max_end = cur.end
        else:
            # 오버랩 그룹 내 — max end 갱신
            group_max_end = max(group_max_end, cur.end)

        if i >= len(ordered) - 1:
            break

        nxt = ordered[i + 1]
        current_gap = nxt.start - cur.end
        effective_gap = nxt.start - group_max_end

        # 자기 자신이 오버랩이 아니고, 그룹 기준 간격이 0 이상 ~ min_gap 미만이면 오류
        if zero_gap <= current_gap and zero_gap <= effective_gap < min_gap:
            errors[cur.index] = (
                f"다음 자막 #{nxt.index} 사이 간격 "
                f"{effective_gap.total_seconds():.3f}초 ({gap_sec}초 미만)"
            )

    return errors

def validate_sync_short_duration(
    start_time: timedelta,
    end_time: timedelta,
    min_duration_sec: float = 1.0,
    **kwargs
) -> bool:
    """
    자막 길이가 min_duration_sec 미만인지 검증

    Args:
        start_time: 시작 시간
        end_time: 종료 시간
        min_duration_sec: 최소 자막 길이 (기본 1.0초)

    Returns:
        True: 오류 (0초 이상 min_duration_sec 미만)
        False: 정상
    """
    if start_time is None or end_time is None:
        return False

    duration = (end_time - start_time).total_seconds()
    return 0 < duration < min_duration_sec

def validate_comma_space(content: str, **kwargs) -> bool:
    """
    쉼표 앞뒤 공백 검증
    - 쉼표(,)의 앞뒤 모두 공백이 없는 경우 오류
    - 앞 또는 뒤 한쪽이라도 공백/줄바꿈이 있으면 정상
    - 줄바꿈은 공백으로 간주
    - 숫자 사이 쉼표(예: 1,000)는 정상 처리
    - 자막 맨 끝 쉼표는 정상 처리
    - 자막 맨 앞 쉼표는 검증 대상

    예시:
    - "안녕,반가워"   → 오류 (앞뒤 모두 공백 없음)
    - "안녕, 반가워"  → 정상 (뒤에 공백)
    - "안녕 ,반가워"  → 정상 (앞에 공백)
    - "안녕 , 반가워" → 정상 (앞뒤 공백)
    - "안녕,\n반가워" → 정상 (뒤에 줄바꿈)
    - "1,000원"      → 정상 (숫자 사이 쉼표)
    - "안녕,"        → 정상 (자막 맨 끝 쉼표)
    - ",안녕"        → 오류 (자막 맨 앞 쉼표, 뒤에 공백 없음)
    - ", 안녕"       → 정상 (자막 맨 앞 쉼표, 뒤에 공백)

    Args:
        content: 자막 내용

    Returns:
        True: 오류 (쉼표 앞뒤 모두 공백 없음)
        False: 정상
    """
    if not content:
        return False

    n = len(content)

    for i, char in enumerate(content):
        if char != ",":
            continue

        # 자막 맨 끝 쉼표는 정상 처리
        if i == n - 1:
            continue

        # 숫자 사이 쉼표는 정상 처리 (예: 1,000)
        prev_is_digit = i > 0 and content[i - 1].isdigit()
        next_is_digit = (i + 1 < n) and content[i + 1].isdigit()
        if prev_is_digit and next_is_digit:
            continue

        # 쉼표 앞 검사 (문자열 시작이거나 공백/줄바꿈이면 OK)
        prev_is_space = (i == 0) or content[i - 1].isspace()

        # 쉼표 뒤 검사 (공백/줄바꿈이면 OK)
        next_is_space = content[i + 1].isspace()

        # 앞뒤 모두 공백이 없으면 오류
        if not prev_is_space and not next_is_space:
            return True

    return False

def validate_line_count_allow_hyphen(
    content: str,
    max_lines: int = 1,
    max_lines_with_hyphen: int = 2,
    hyphen_prefix: str = "-",
    **kwargs
) -> bool:
    """
    자막 줄 수 검증 (하이픈 오버랩 예외 허용)
    
    검증 규칙:
    - 기본: max_lines 초과 시 오류 (기본값 1줄)
    - 예외: 모든 줄이 hyphen_prefix로 시작하면 max_lines_with_hyphen까지 허용 (기본값 2줄)
    - 부분적으로 하이픈이 있는 경우는 오류 (모든 줄이 시작해야 예외 적용)
    
    Args:
        content: 자막 내용
        max_lines: 기본 최대 줄 수 (기본값 1)
        max_lines_with_hyphen: 하이픈 시 최대 줄 수 (기본값 2)
        hyphen_prefix: 하이픈 판별 접두사 (기본값 "-")
    
    Returns:
        True: 줄 수 초과 (오류)
        False: 정상
    
    예시:
    - "안녕하세요"                       → False (정상, 1줄)
    - "안녕하세요\n반갑습니다"            → True  (오류, 2줄, 하이픈 없음)
    - "-안녕하세요\n-반갑습니다"        → False (정상, 2줄, 모두 하이픈)
    - "-안녕하세요\n반갑습니다"          → True  (오류, 두 번째 줄 하이픈 없음)
    - "-안녕\n-반갑\n-하이"           → True  (오류, 3줄 초과)
    - "-안녕하세요"                     → False (정상, 1줄)
    """
    if not content:
        return False
    
    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    non_empty_count = len(non_empty_lines)
    
    # 기본 최대 줄 수 이내면 정상
    if non_empty_count <= max_lines:
        return False
    
    # 하이픈 예외 체크: 모든 비어있지 않은 줄이 hyphen_prefix로 시작하는가?
    all_lines_have_hyphen = all(
        line.strip().startswith(hyphen_prefix) 
        for line in non_empty_lines
    )
    
    # 모든 줄이 하이픈으로 시작 + 줄 수가 max_lines_with_hyphen 이내면 정상
    if all_lines_have_hyphen and non_empty_count <= max_lines_with_hyphen:
        return False
    
    # 그 외 모두 오류
    return True


# ============================================================
# 최종 납품 후처리  (postprocess_final.py)
# ============================================================

def postprocess_add_banner_subtitle(
    subtitles: List[srt.Subtitle],
    banner_sentence: str,
    banner_start: str = "00:00:00,000",
    banner_end: str = "00:05:00,000",
    **kwargs
) -> List[srt.Subtitle]:
    """
    배너 싱크 추가 (JTBC/TVCS용)
    
    Args:
        subtitles: 자막 리스트
        banner_sentence: 배너 문장
        banner_start: 배너 시작 시간 (SRT 형식)
        banner_end: 배너 종료 시간 (SRT 형식)
    
    Returns:
        배너가 추가된 자막 리스트
    """
    if not subtitles:
        return subtitles
    
    start_td = parse_srt_time(banner_start)
    end_td = parse_srt_time(banner_end)
    
    # 배너 자막 생성
    banner_subtitle = srt.Subtitle(
        index=0,  # 임시 인덱스
        start=start_td,
        end=end_td,
        content=banner_sentence
    )
    
    # 맨 앞에 배너 추가
    result = [banner_subtitle] + subtitles
    
    # 인덱스 재부여
    # return srt.sort_and_reindex(result)
    # 인덱스 재부여
    result_sorted = sorted(result, key=lambda s: (s.start, s.end))
    for new_index, sub in enumerate(result_sorted, start=1):
        sub.index = new_index
    return result_sorted

# NOTE: postprocess_remove_last_punctuation — postprocess_stage2.py 판을 덮어씀 (mediaflow import 순서와 동일)

def postprocess_remove_last_punctuation(
    sentence: str,
    punctuation: List[str] = None,
    **kwargs
) -> str:
    """
    단일 구두점 제거
    - 문장 내 모든 '단일' 구두점을 제거 (기본 '.')
    - 예외: 말줄임표 '...', 숫자.숫자, 영어.영어 는 보존
    
    Args:
        sentence: 처리할 문장
        punctuation: 제거할 구두점 리스트
    
    Returns:
        구두점이 제거된 문장
    """
    if sentence is None:
        return ""
    
    if punctuation is None:
        punctuation = ["."]

    lines = sentence.splitlines()
    out = []

    for line in lines:
        raw = line
        s = raw.rstrip()

        if not s:
            out.append(raw)
            continue

        result = []
        i = 0
        while i < len(s):
            ch = s[i]

            if ch in punctuation:
                # 말줄임표 보존: 연속된 마침표(2개 이상)
                if ch == "." and i + 1 < len(s) and s[i + 1] == ".":
                    while i < len(s) and s[i] == ".":
                        result.append(s[i])
                        i += 1
                    continue

                # 숫자.숫자 보존
                prev_char = s[i - 1] if i > 0 else ""
                next_char = s[i + 1] if i + 1 < len(s) else ""

                if prev_char.isdigit() and next_char.isdigit():
                    result.append(ch)
                    i += 1
                    continue

                # 영어.영어 보존
                if prev_char.isascii() and prev_char.isalpha() and \
                   next_char.isascii() and next_char.isalpha():
                    result.append(ch)
                    i += 1
                    continue

                # 그 외 단일 구두점 제거
                i += 1
                continue

            result.append(ch)
            i += 1

        out.append("".join(result))

    return "\n".join(out)
