"""
공유받은 소스 파일들에서 함수 단위로 코드를 추출하여
seed_source_codes.py를 자동 생성하는 스크립트.

Usage: python -m app.generate_source_codes
"""
import re
import os

def extract_functions_from_source(source_text):
    """파이썬 소스에서 최상위 def/주석달린 def 단위로 함수를 추출"""
    functions = {}
    lines = source_text.split('\n')
    current_func = None
    current_lines = []
    # 함수 앞의 주석도 포함
    pending_comments = []
    
    for line in lines:
        # 주석이 달린 함수 시작 (#로 시작하는 줄 무시하되 def 바로 앞 주석은 보존)
        
        # 새 함수 시작 감지 (최상위 레벨 def)
        match = re.match(r'^def\s+(\w+)\s*\(', line)
        if match:
            # 이전 함수 저장
            if current_func:
                functions[current_func] = '\n'.join(current_lines).rstrip()
            current_func = match.group(1)
            current_lines = [line]
            pending_comments = []
            continue
        
        if current_func:
            # 빈 줄
            if not line.strip():
                current_lines.append(line)
                continue
            # 들여쓰기 있으면 함수 본문
            if line.startswith(' ') or line.startswith('\t'):
                current_lines.append(line)
            # 주석 줄 (# 으로 시작, 들여쓰기 없음) → 함수 끝
            elif line.startswith('#'):
                functions[current_func] = '\n'.join(current_lines).rstrip()
                current_func = None
                current_lines = []
            # 다른 최상위 코드 → 함수 끝
            else:
                functions[current_func] = '\n'.join(current_lines).rstrip()
                current_func = None
                current_lines = []
    
    # 마지막 함수
    if current_func:
        functions[current_func] = '\n'.join(current_lines).rstrip()
    
    return functions


# 소스 코드 (문서에서 공유받은 내용)
SOURCES = {}

# postprocess_common.py
SOURCES["postprocess_common"] = r'''
def postprocess_strip_whitespace(sentence: str, **kwargs) -> str:
    """문장 앞뒤 공백 제거"""
    return sentence.strip()


def postprocess_normalize_spaces(sentence: str, **kwargs) -> str:
    """연속된 공백을 단일 공백으로 정규화"""
    return re.sub(r"[^\S\r\n]{2,}", " ", sentence)


def postprocess_normalize_wrong_mixed_punctuations(sentence, **kwargs) -> str:
    """잘못된 특수문자/구두점/오탈자 표기를 정규화"""
    if sentence is None:
        return ""
    return (
        sentence.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\uff0e", ".")
        .replace("\u201c", "")
        .replace("\u201d", "")
        .replace("\uff02", "")
        .replace("\u00b7", ".")
        .replace("\uacd8", "\uacb0")
        .replace("\uaf10", "\uaed8")
    )


def postprocess_add_space_after_special_punctuation(sentence: str, **kwargs) -> str:
    """... ? ! 뒤에 바로 글자가 오면 공백 1칸 추가 (맨 앞은 제외)"""
    if sentence is None:
        return ""
    def _repl(m):
        if m.start(1) == 0:
            return m.group(1) + m.group(2)
        return f"{m.group(1)} {m.group(2)}"
    pattern1 = re.compile(r'(\.{3,}|[?!])([가-힣A-Za-z0-9])')
    pattern2 = re.compile(r'(?<!\d)(~)([가-힣A-Za-z0-9])')
    lines = sentence.splitlines()
    out_lines = []
    for line in lines:
        new_line = pattern1.sub(_repl, line)
        new_line = pattern2.sub(_repl, new_line)
        out_lines.append(new_line)
    return "\n".join(out_lines)


def postprocess_trim_speaker_spaces(sentence: str, **kwargs) -> str:
    """괄호 안쪽 공백 제거"""
    sentence = re.sub(r"\(\s+", "(", sentence)
    sentence = re.sub(r"\s+\)", ")", sentence)
    sentence = re.sub(r"\[\s+", "[", sentence)
    sentence = re.sub(r"\s+\]", "]", sentence)
    return sentence


def postprocess_add_speaker_space(sentence: str, **kwargs) -> str:
    """화자 표시 닫는 괄호 뒤 공백 추가"""
    return re.sub(r"\)([^\s\[\(])", r") \1", sentence)


def postprocess_normalize_ellipsis(sentence: str, **kwargs) -> str:
    """말줄임표 정규화: 4개 이상 → 3개"""
    def _replace_dots(match):
        dots = match.group(0)
        count = len(dots)
        if count >= 4:
            return "..."
        if count == 3:
            return "..."
        return dots
    result = re.sub(r"\.{2,}", _replace_dots, sentence)
    result = re.sub(r"\s+$", "", result)
    return result


def postprocess_remove_wrong_punctuation(sentence: str, **kwargs) -> str:
    """문장 앞의 . ... ? ! ~ 제거, 끝 쉼표 삭제, '..' 유지"""
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
        line_text = re.sub(r"\.\.", _keep, line_text)
        line_text = re.sub(r"^[\.\?\!~]+\s*", "", line_text)
        line_text = re.sub(
            r"\uE000(\d+)\uE001",
            lambda m: kept[int(m.group(1))],
            line_text,
        )
        out.append(line_text)
    if out:
        out[-1] = re.sub(r",\s*$", "", out[-1])
    return "\n".join(out)


def postprocess_normalize_repeats(sentence, **kwargs) -> str:
    """같은 특수기호 반복을 1개로 축약 (! ? , ~)"""
    if sentence is None:
        return ""
    return re.sub(r"([!?,~])\1+", r"\1", sentence)


def postprocess_normalize_mix_characters(sentence, pattern=r"[!?.,~]+", **kwargs) -> str:
    """혼합 특수기호 런을 마지막 단위만 남김"""
    if sentence is None:
        return ""
    tail_unit = re.compile(r"(?:\.\.\.|\.|[!?~,])$")
    def _collapse_run(m):
        run = m.group(0)
        if run == "..":
            return run
        last = tail_unit.search(run).group(0)
        return "..." if last == "..." else last
    return re.sub(pattern, _collapse_run, sentence)


def postprocess_sync_overlap(front_end_time, back_start_time, **kwargs):
    """앞 종료==뒤 시작이면 앞 종료를 10ms 당김"""
    from datetime import timedelta
    if front_end_time == back_start_time:
        adjusted = front_end_time - timedelta(milliseconds=10)
        if adjusted < timedelta(0):
            adjusted = timedelta(0)
        return adjusted
    return front_end_time


def postprocess_reset_subtitles_from_list(subtitles, **kwargs):
    """리스트 기반 인덱스 재부여 + 시간 순 정렬"""
    if not subtitles:
        return []
    subtitles_sorted = sorted(subtitles, key=lambda s: s.start)
    for i, sub in enumerate(subtitles_sorted, start=1):
        sub.index = i
    return subtitles_sorted
'''

# validate_common.py
SOURCES["validate_common"] = r'''
def validate_length(sentence, max_length=18, weight_kor=1.0, weight_etc=1.0, **kwargs):
    """문장 길이 검증 (가중치 적용 가능)"""
    if weight_kor == 1.0 and weight_etc == 1.0:
        return len(sentence) > max_length
    total_length = 0
    for ch in sentence:
        if "\uAC00" <= ch <= "\uD7A3":
            total_length += weight_kor
        else:
            total_length += weight_etc
    return total_length > max_length


def validate_length_lines(content, max_length=18, valid_type="length", weight_kor=1.0, weight_etc=1.0, **kwargs):
    """줄별 길이 검증"""
    for sentence in content.split("\n"):
        if valid_type == "length":
            if validate_length(sentence, max_length, weight_kor, weight_etc):
                return True
        elif valid_type == "byte":
            if len(sentence.encode("utf-8")) > max_length * 2:
                return True
    return False


def validate_line_count(content, max_lines=2, **kwargs):
    """자막 줄 수 검증"""
    return max_lines <= content.count("\n")


def validate_pair_characters(content, pair_char=None, **kwargs):
    """괄호/따옴표/음표 짝 검증"""
    if not content:
        return False
    if pair_char is None:
        pair_char = {"(": ")", "[": "]", "<": ">", "\u266A": "\u266A"}
    s = content.replace("\n", " ")
    for ch, close in pair_char.items():
        if ch == close:
            if s.count(ch) % 2 == 1:
                return True
    open_to_close = {o: c for o, c in pair_char.items() if o != c}
    close_to_open = {c: o for o, c in open_to_close.items()}
    stack = []
    for ch in s:
        if ch in open_to_close:
            stack.append(ch)
        elif ch in close_to_open:
            if not stack:
                return True
            top = stack.pop()
            if open_to_close[top] != ch:
                return True
    return len(stack) != 0


def validate_special_characters_allow_music_note(content, **kwargs):
    """사용 불가 특수 문자 검증 (\u266B는 허용)"""
    import string
    content = content.replace("\n", " ").replace("\u2018", "'").replace("\u2019", "'")
    punctuation_without_slash = string.punctuation.replace("/", "")
    ansi_chars = (
        "".join(chr(i) for i in range(0xAC00, 0xD7A4))
        + string.ascii_letters + string.digits + punctuation_without_slash + " "
    )
    for char in content:
        if char == "\u266A":
            continue
        if char not in ansi_chars:
            return True
        if char == "/":
            return True
    return False


def validate_sync_negative_or_zero(start_time, end_time, **kwargs):
    """싱크 시간이 마이너스 혹은 0인지 확인"""
    return True if start_time >= end_time else False


def validate_ellipsis_count(content, criterion=2, **kwargs):
    """말줄임표의 마침표 개수 검증"""
    content = content.replace("\n", " ")
    matches = re.findall(r"\.{2,}", content)
    for m in matches:
        if len(m) == criterion:
            return True
    return False
'''

# validate_stage2.py
SOURCES["validate_stage2"] = r'''
def validate_special_characters(content, **kwargs):
    """사용할 수 없는 특수 기호 검증 (음표 미허용)"""
    import string
    content = content.replace("\n", " ")
    ansi_chars = (
        "".join(chr(i) for i in range(0xAC00, 0xD7A4))
        + string.ascii_letters + string.digits + string.punctuation + " "
    )
    for char in content:
        if char not in ansi_chars:
            return True
    return False


def validate_overlapped_over_lines(front_content, back_content, front_end_time, back_start_time, max_lines=2):
    """오버랩 + n줄 검증"""
    if front_end_time <= back_start_time:
        return False
    def _lc(text):
        if not text or not text.strip():
            return 0
        return text.count("\n") + 1
    return _lc(front_content) >= max_lines or _lc(back_content) >= max_lines


def validate_hyphen_no_space_after_for_skbb(content, **kwargs):
    """하이픈 사용 규칙 검증: 줄 시작 '-' 다음에 공백이 오면 오류"""
    if not content:
        return False
    for line in content.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("-"):
            continue
        if len(stripped) > 1 and stripped[1].isspace():
            return True
    return False


def validate_mosaic_count_for_skbb(content, criterion=2, **kwargs):
    """모자이크(*) 개수 검증"""
    if not content:
        return False
    star_groups = re.findall(r"\*+", content)
    if not star_groups:
        return False
    for group in star_groups:
        if len(group) != criterion:
            return True
    return False


def validate_sync_overlapped(front_content, back_content, front_end_time, back_start_time, **kwargs):
    """오버랩(싱크 겹침) 검증"""
    if front_end_time is None or back_start_time is None:
        return False
    return front_end_time > back_start_time


def validate_overlapped_only_text_for_lghv(front_content, back_content, front_end_time, back_start_time, **kwargs):
    """LGHV: 오버랩된 싱크가 대사+대사인지 확인 (대괄호 태그 포함 시 오류)"""
    if front_end_time <= back_start_time:
        return False
    def _single(t):
        return t is not None and "\n" not in t.strip()
    def _bracket(t):
        if t is None: return False
        s = t.strip()
        return s.startswith("[") and s.endswith("]") and len(s) > 2
    if not (_single(front_content) and _single(back_content)):
        return False
    return _bracket(front_content) or _bracket(back_content)


def validate_overlapped_accumulated_lines(subtitles, max_lines=3, **kwargs):
    """연속 오버랩 그룹의 누적 줄 수 검사"""
    if not subtitles:
        return {}
    ordered = sorted(subtitles, key=lambda x: (x.start, x.end, x.index))
    errors = {}
    def _lc(t):
        if not t or not t.strip(): return 0
        return t.count("\n") + 1
    def _flush(group):
        if len(group) < 2: return
        total = sum(_lc(s.content) for s in group)
        if total <= max_lines: return
        detail = f"연속 오버랩 총 {total}줄 ({max_lines}줄 초과)"
        for s in group:
            errors[s.index] = detail
    current_group, current_end = [], None
    for sub in ordered:
        if not current_group:
            current_group, current_end = [sub], sub.end
            continue
        if sub.start < current_end:
            current_group.append(sub)
            if sub.end > current_end: current_end = sub.end
        else:
            _flush(current_group)
            current_group, current_end = [sub], sub.end
    _flush(current_group)
    return errors


def validate_sync_short_duration(start_time, end_time, min_duration_sec=1.0, **kwargs):
    """자막 길이가 min_duration_sec 미만인지 검증"""
    if start_time is None or end_time is None:
        return False
    duration = (end_time - start_time).total_seconds()
    return 0 < duration < min_duration_sec
'''

# postprocess_stage2.py (주요 함수들)
SOURCES["postprocess_stage2"] = r'''
def postprocess_merge_overlapped_sync(subs, max_lines_per_sub=1, **kwargs):
    """오버랩 자막 병합 (겹침만 처리, 맞닿음은 제외)"""
    if not subs:
        return subs
    def _within(text):
        if text is None: return False
        return text.strip().count("\n") < max_lines_per_sub
    subs = sorted(subs, key=lambda x: (x.start, x.end))
    result, i, n = [], 0, len(subs)
    while i < n:
        cur = subs[i]
        if i == n - 1:
            result.append(cur); break
        nxt = subs[i + 1]
        if cur.end > nxt.start and _within(cur.content) and _within(nxt.content):
            import srt
            merged = srt.Subtitle(index=cur.index, start=cur.start,
                end=max(cur.end, nxt.end), content=f"{cur.content}\n{nxt.content}")
            result.append(merged); i += 2
        else:
            result.append(cur); i += 1
    return result


def postprocess_convert_characters(text, from_chars="[]", to_chars="()", **kwargs):
    """기호 변경 (예: [] -> ())"""
    if text is None: return ""
    if len(from_chars) == len(to_chars):
        return text.translate(str.maketrans(from_chars, to_chars))
    return text


def postprocess_remove_last_punctuation(sentence, punctuation=None, **kwargs):
    """마지막 구두점 제거 (말줄임표 '...' 보존)"""
    if sentence is None: return ""
    if punctuation is None: punctuation = ["."]
    lines = sentence.splitlines()
    out = []
    for line in lines:
        s = line.rstrip()
        if not s or s.endswith("..."):
            out.append(line); continue
        if s[-1] in punctuation:
            s = s[:-1]
        out.append(s)
    return "\n".join(out)


def postprocess_remove_not_pair_characters(content, pair_char=None, **kwargs):
    """한쌍이 아니면 삭제 (괄호/따옴표/기호)"""
    if content is None: return ""
    if pair_char is None:
        pair_char = {"(": ")", "[": "]", '"': '"', "'": "'", "<": ">", "\u266A": "\u266A"}
    flat = content.replace("\n", " ")
    text = content
    for open_char, close_char in pair_char.items():
        open_count = flat.count(open_char)
        close_count = flat.count(close_char)
        if open_char == close_char:
            if open_count % 2 != 0:
                text = text.replace(open_char, "")
            continue
        if open_count != close_count:
            text = text.replace(open_char, "").replace(close_char, "")
    return text


def postprocess_remove_mid_period(sentence, **kwargs):
    """문장 중간 마침표 제거 (소수/말줄임표/'..' 제외)"""
    if sentence is None: return ""
    lines = sentence.splitlines()
    out = []
    for line in lines:
        lt = line; kept = []
        def _keep(m):
            kept.append(m.group(0))
            return f"\uE000{len(kept)-1}\uE001"
        lt = re.sub(r"\.{3,}", _keep, lt)
        lt = re.sub(r"\.\.", _keep, lt)
        lt = re.sub(r"(?<!\d)\.(?!\d)(?!\s*$)", "", lt)
        lt = re.sub(r"\uE000(\d+)\uE001", lambda m: kept[int(m.group(1))], lt)
        out.append(lt)
    return "\n".join(out)


def postprocess_add_period_between_subs(subs, ending_punctuation=".!?~", **kwargs):
    """자막 간 마침표 삽입"""
    if not subs: return subs
    for i in range(len(subs) - 1):
        cur, nxt = subs[i], subs[i + 1]
        if not cur.content or not nxt.content: continue
        nxt_first = nxt.content.splitlines()[0].strip()
        if not (nxt_first.startswith("-") or nxt_first.startswith("(")): continue
        cur_lines = cur.content.splitlines()
        last = cur_lines[-1].rstrip()
        if not last or last.endswith("...") or last[-1] in ending_punctuation or last[-1] in ")]": continue
        cur_lines[-1] = last + "."
        cur.content = "\n".join(cur_lines)
    return subs


def postprocess_add_period_between_lines(sentence, ending_punctuation=".!?~", **kwargs):
    """줄 간 마침표 삽입"""
    if sentence is None: return ""
    lines = sentence.splitlines()
    if len(lines) < 2: return sentence
    for i in range(len(lines) - 1):
        cur = lines[i].rstrip()
        nxt = lines[i + 1].strip()
        if not cur or not nxt: continue
        if not (nxt.startswith("-") or nxt.startswith("(")): continue
        if cur.endswith("...") or cur[-1] in ending_punctuation or cur[-1] in ")]": continue
        lines[i] = cur + "."
    return "\n".join(lines)


def postprocess_remove_other_characters(text, **kwargs):
    """JTBC: 통합 기호 제거 (*, ♪, ♫, [], (), <>, ^)"""
    if text is None: return ""
    out = re.sub(r"[\*\u266A\u266B\[\]\(\)<>\^]", "", text)
    return out


def postprocess_normalize_asterisk_for_skbb(sentence, **kwargs):
    """SKBB: 별표 정규화 (2개 이상→**, 1개→그대로)"""
    def repl(m):
        return "**" if len(m.group(0)) >= 2 else "asterisks"
    result = re.sub(r"\*{2,}", repl, sentence)
    return re.sub(r"\s+$", "", result)


def postprocess_remove_star_and_angle_for_skbb(text, **kwargs):
    """SKBB: 큰따옴표, 음표, 소괄호, 꺾쇠 제거"""
    if text is None: return ""
    return re.sub(r'["\u266A\u266B\(\)<>]', "", text)


def postprocess_remove_not_pair_paren_quotes_for_skbb(text, **kwargs):
    """SKBB: 짝 안 맞는 작은따옴표, 꺾쇠만 제거"""
    if text is None: return ""
    return postprocess_remove_not_pair_characters(text, pair_char={"'": "'", "<": ">"})


def postprocess_remove_star_and_angle_for_lghv(text, **kwargs):
    """LGHV: 별표와 꺾쇠 제거"""
    if text is None: return ""
    return re.sub(r"[\*<>]", "", text)


def postprocess_remove_not_pair_paren_quotes_for_lghv(text, **kwargs):
    """LGHV: 짝 안 맞는 괄호/따옴표 제거"""
    if text is None: return ""
    return postprocess_remove_not_pair_characters(text, pair_char={"(": ")", '"': '"', "'": "'"})


def postprocess_normalize_music_to_double_note_for_lghv(text, **kwargs):
    """LGHV: 음표 통일 (♫로)"""
    if text is None: return ""
    return re.sub(r"[\u266A\u266B\u266C\u266D\u266E\u266F]", "\u266B", text)


def postprocess_keep_bracket_music_note_and_remove_others_for_lghv(text, **kwargs):
    """LGHV: [♫ ...]만 살리고 나머지 음표 제거"""
    if text is None: return ""
    SENTINEL = "\uE000"
    out = re.sub(r"\[\u266B\s*", "[\u266B ", text)
    out = out.replace("[\u266B ", f"[{SENTINEL} ")
    out = re.sub(r"[\u266B]", "", out)
    out = out.replace(f"[{SENTINEL} ", "[\u266B ")
    return out


def postprocess_normalize_music_to_single_note_for_tvng(text, **kwargs):
    """TVING: 음표 통일 (♪로)"""
    if text is None: return ""
    return re.sub(r"[\u266A\u266B\u266C\u266D\u266E\u266F]", "\u266A", text)


def postprocess_over_length_lines(text, max_length=18, **kwargs):
    """18글자 기준 줄바꿈"""
    if text is None: return ""
    lines = text.splitlines()
    out = []
    for line in lines:
        if not line or len(line) <= max_length:
            out.append(line); continue
        words = line.split()
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if len(candidate) > max_length and current:
                out.append(current); current = word
            else:
                current = candidate
        if current:
            out.append(current)
    return "\n".join(out)


def postprocess_mark_overlapped_multi_speaker(subs, reassign_index=True, multi_speaker_prefix="- ", max_lines_per_sub=1, multi_overlap_strategy="best_pair", max_merged_lines=2, **kwargs):
    """오버랩 다화자 구간 처리 (2개: 하이픈 추가 후 병합, 3개+: 전략별 처리)"""
    # 실제 코드는 postprocess_stage2.py 참조 (약 200줄)
    pass


def postprocess_remove_first_hypn(sentence, punctuation=None, **kwargs):
    """SKBB: 첫 자막의 시작 하이픈 제거"""
    if not sentence: return sentence
    subtitle_index = kwargs.get('subtitle_index', None)
    if subtitle_index is None or subtitle_index != 1: return sentence
    if punctuation is None: punctuation = "-"
    i = 0
    while i < len(sentence) and sentence[i].isspace(): i += 1
    if i < len(sentence) and sentence[i] in punctuation:
        return sentence[:i] + sentence[i+1:]
    return sentence


def postprocess_remove_space_after_hypn(sentence, **kwargs):
    """맨 앞 하이픈 뒤 공백 제거"""
    if sentence is None: return ""
    lines = sentence.splitlines()
    out = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("- "):
            stripped = "-" + stripped[2:]
        out.append(stripped)
    return "\n".join(out)


def postprocess_adjust_or_merge_short_sync(subs, min_duration_sec=1.0, max_lines_after_merge=3, gap_sec=0.083, **kwargs):
    """DLIV: 1초 미만 자막 처리 (연장 또는 병합)"""
    # 실제 코드는 postprocess_stage2.py 참조 (약 100줄)
    pass


def postprocess_adjust_subtitle_gaps(subs, gap_sec=0.083, **kwargs):
    """DLIV: 자막 간격 조정 (gap_sec 미만이면 앞 자막 end 조정)"""
    # 실제 코드는 postprocess_stage2.py 참조
    pass
'''


def generate():
    all_funcs = {}
    for source_name, source_text in SOURCES.items():
        funcs = extract_functions_from_source(source_text)
        print(f"  {source_name}: {len(funcs)} functions")
        for fname, code in funcs.items():
            all_funcs[fname] = code
    
    # seed_source_codes.py 생성
    out_lines = [
        '"""',
        '함수명 → 소스코드 매핑 (자동 생성)',
        '"""',
        '',
        'SOURCE_CODES = {',
    ]
    
    for fname, code in sorted(all_funcs.items()):
        escaped = code.replace('\\', '\\\\').replace("'''", "\\'\\'\\'\\'")
        out_lines.append(f'    "{fname}": {repr(code)},')
        out_lines.append('')
    
    out_lines.append('}')
    
    output_path = os.path.join(os.path.dirname(__file__), 'seed_source_codes.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    
    print(f"\n✅ Generated {output_path} with {len(all_funcs)} functions")


if __name__ == "__main__":
    generate()
