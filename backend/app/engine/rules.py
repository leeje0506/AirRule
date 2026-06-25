"""
AirRule 테스트 엔진 — 실제 후처리/검증 함수 모음 (실제 파이프라인 소스 이식).
subtitle_common 의존부는 아래 shim 으로 대체. srt 라이브러리 필요: pip install srt
"""
import re
import string
import unicodedata
import logging
from datetime import timedelta
from typing import List, Dict, Optional

import srt

logger = logging.getLogger(__name__)


# ============================================================
# subtitle_common shim
# ============================================================

_STYLE_TAG_RE = re.compile(r"\{[^}]*\}")


def strip_style_tags(text):
    if not text:
        return text or ""
    return _STYLE_TAG_RE.sub("", text)


def replace_linebreak(content, repl=" "):
    if content is None:
        return ""
    return content.replace("\n", repl)


def get_origin_indices(sub):
    return getattr(sub, "_origin_indices", [sub.index])


def set_origin_indices(sub, indices):
    sub._origin_indices = list(indices)


def parse_srt_time(s: str) -> timedelta:
    s = (s or "").strip().replace(".", ",")
    if "," in s:
        hms, ms = s.split(",", 1)
    else:
        hms, ms = s, "0"
    parts = hms.split(":")
    while len(parts) < 3:
        parts = ["0"] + parts
    h, m, sec = parts[-3], parts[-2], parts[-1]
    ms = (ms + "000")[:3]
    return timedelta(hours=int(h), minutes=int(m), seconds=int(sec), milliseconds=int(ms))


# ============================================================
# 1차 공통 후처리 / 검증 (postprocess_common, validate_common)
# ============================================================

def postprocess_strip_whitespace(sentence: str, **kwargs) -> str:
    return sentence.strip()


def postprocess_normalize_spaces(sentence: str, **kwargs) -> str:
    return re.sub(r"[^\S\r\n]{2,}", " ", sentence)


def postprocess_normalize_wrong_mixed_punctuations(sentence: Optional[str], **kwargs) -> str:
    if sentence is None:
        return ""
    return (
        sentence.replace("\u2018", "'").replace("\u2019", "'").replace("\uff0e", ".")
        .replace('"', "").replace("\u201c", "").replace("\u201d", "").replace("\uff02", "")
        .replace("\u00b7", ".").replace("\uacd8", "\uaca0").replace("\uaf10", "\uaed8")
    )


def postprocess_add_space_after_special_punctuation(sentence: str, **kwargs) -> str:
    if sentence is None:
        return ""

    def _repl(m):
        if m.start(1) == 0:
            return m.group(1) + m.group(2)
        return f"{m.group(1)} {m.group(2)}"

    p1 = re.compile(r'(\.{3,}|[?!])([\uac00-\ud7a3A-Za-z0-9])')
    p2 = re.compile(r'(?<!\d)(~)([\uac00-\ud7a3A-Za-z0-9])')
    out = []
    for line in sentence.splitlines():
        line = p1.sub(_repl, line)
        line = p2.sub(_repl, line)
        out.append(line)
    return "\n".join(out)


def postprocess_trim_speaker_spaces(sentence: str, **kwargs) -> str:
    sentence = re.sub(r"\(\s+", "(", sentence)
    sentence = re.sub(r"\s+\)", ")", sentence)
    sentence = re.sub(r"\[\s+", "[", sentence)
    sentence = re.sub(r"\s+\]", "]", sentence)
    return sentence


def postprocess_add_speaker_space(sentence: str, **kwargs) -> str:
    return re.sub(r"\)([^\s\[\(])", r") \1", sentence)


def postprocess_normalize_ellipsis(sentence: str, **kwargs) -> str:
    def _r(m):
        c = len(m.group(0))
        return "..." if c >= 3 else m.group(0)
    result = re.sub(r"\.{2,}", _r, sentence)
    return re.sub(r"\s+$", "", result)


def postprocess_remove_wrong_punctuation(sentence: str, **kwargs) -> str:
    if sentence is None:
        return ""
    lines = sentence.splitlines()
    out = []
    for line in lines:
        kept = []

        def _keep(m):
            kept.append(m.group(0))
            return f"\ue000{len(kept) - 1}\ue001"

        line = re.sub(r"\.\.", _keep, line)
        line = re.sub(r"^[\.\?\!~]+\s*", "", line)
        line = re.sub(r"\ue000(\d+)\ue001", lambda m: kept[int(m.group(1))], line)
        out.append(line)
    if out:
        out[-1] = re.sub(r",\s*$", "", out[-1])
    return "\n".join(out)


def postprocess_normalize_repeats(sentence: Optional[str], **kwargs) -> str:
    if sentence is None:
        return ""
    return re.sub(r"([!?,~])\1+", r"\1", sentence)


def postprocess_normalize_mix_characters(sentence: Optional[str], pattern: str = r"[!?.,~]+", **kwargs) -> str:
    if sentence is None:
        return ""

    def _c(m):
        run = m.group(0)
        if run == "..":
            return run
        if run.count(".") >= 2:
            return "..."
        return run[-1]
    return re.sub(pattern, _c, sentence)


def postprocess_sync_overlap(front_end_time: timedelta, back_start_time: timedelta, **kwargs):
    if front_end_time == back_start_time:
        adjusted = front_end_time - timedelta(milliseconds=10)
        return adjusted if adjusted >= timedelta(0) else timedelta(0)
    return front_end_time


def postprocess_reset_subtitles_from_list(subtitles: List[srt.Subtitle], **kwargs) -> List[srt.Subtitle]:
    if not subtitles:
        return []
    s = sorted(subtitles, key=lambda x: x.start)
    for i, sub in enumerate(s, start=1):
        sub.index = i
    return s


def postprocess_fix_yae_yee(sentence: str, **kwargs) -> str:
    if not sentence:
        return sentence
    sentence = unicodedata.normalize("NFC", sentence)
    BASE, END = 0xAC00, 0xD7A3
    YAE, YEE, AE, E, SS = 3, 7, 1, 5, 20
    NJ, NJO = 21, 28
    out = []
    for ch in sentence:
        code = ord(ch)
        if not (BASE <= code <= END):
            out.append(ch); continue
        si = code - BASE
        cho = si // (NJ * NJO)
        jung = (si % (NJ * NJO)) // NJO
        jong = si % NJO
        if jong == SS and jung in (YAE, YEE):
            nj = AE if jung == YAE else E
            out.append(chr(BASE + cho * NJ * NJO + nj * NJO + jong))
        else:
            out.append(ch)
    return "".join(out)


def postprocess_fix_position_tag(sentence: str, **kwargs) -> str:
    if not sentence:
        return sentence
    p1 = re.compile(r"\{\s*[\\/]+\s*(?:\ubb34|an)\s*8\s*\}?", re.IGNORECASE)
    sentence = p1.sub(r"{\\an8}", sentence)
    p2 = re.compile(r"\{[\x00-\x1F\s]*(?:\ubb34|a?n)\s*8\s*\}", re.IGNORECASE)
    sentence = p2.sub(r"{\\an8}", sentence)
    return sentence


def postprocess_normalize_comma_space(sentence: Optional[str], **kwargs) -> str:
    if sentence is None:
        return ""
    out = []
    i, n = 0, len(sentence)
    while i < n:
        ch = sentence[i]
        if ch != ",":
            out.append(ch); i += 1; continue
        prev_d = i > 0 and sentence[i - 1].isdigit()
        next_d = i + 1 < n and sentence[i + 1].isdigit()
        if prev_d and next_d:
            out.append(ch); i += 1; continue
        if i == n - 1:
            out.append(ch); i += 1; continue
        while out and out[-1] in (" ", "\t"):
            out.pop()
        out.append(",")
        nc = sentence[i + 1]
        if nc in ("\n", "\r"):
            i += 1; continue
        if nc in (" ", "\t"):
            j = i + 1
            while j < n and sentence[j] in (" ", "\t"):
                j += 1
            if j < n and sentence[j] not in ("\n", "\r"):
                out.append(" ")
            i = j; continue
        out.append(" "); i += 1
    return "".join(out)


def validate_length(sentence: str, max_length: int = 18, weight_kor: float = 1.0, weight_etc: float = 1.0, **kwargs) -> bool:
    sentence = strip_style_tags(sentence)
    if weight_kor == 1.0 and weight_etc == 1.0:
        return len(sentence) > max_length
    total = 0
    for ch in sentence:
        total += weight_kor if "\uac00" <= ch <= "\ud7a3" else weight_etc
    return total > max_length


def validate_byte_length(sentence: str, max_length: int = 36, **kwargs) -> bool:
    sentence = strip_style_tags(sentence)
    return max_length < len(sentence.encode("utf-8"))


def validate_length_lines(content: str, max_length: int = 18, valid_type: str = "length", weight_kor: float = 1.0, weight_etc: float = 1.0, **kwargs) -> bool:
    for sentence in content.split("\n"):
        if valid_type == "length":
            if validate_length(sentence, max_length, weight_kor, weight_etc):
                return True
        elif valid_type == "byte":
            if validate_byte_length(sentence):
                return True
    return False


def validate_line_count(content: str, max_lines: int = 2, **kwargs) -> bool:
    return max_lines <= content.count("\n")


def validate_pair_characters(content: str, pair_char: Optional[Dict[str, str]] = None, **kwargs) -> bool:
    if not content:
        return False
    if pair_char is None:
        pair_char = {"(": ")", "[": "]", "<": ">", "\u266a": "\u266a"}
    s = content.replace("\n", " ")
    for ch, close in pair_char.items():
        if ch == close and s.count(ch) % 2 == 1:
            return True
    open_to_close = {o: c for o, c in pair_char.items() if o != c}
    close_to_open = {c: o for o, c in open_to_close.items()}
    stack: List[str] = []
    for ch in s:
        if ch in open_to_close:
            stack.append(ch); continue
        if ch in close_to_open:
            if not stack:
                return True
            top = stack.pop()
            if open_to_close[top] != ch:
                return True
    return len(stack) != 0


def validate_special_characters_allow_music_note(content: str, **kwargs) -> bool:
    content = content.replace("\n", " ").replace("\u2019", "'").replace("\u2018", "'")
    punct = string.punctuation.replace("/", "")
    ansi = ("".join(chr(i) for i in range(0xAC00, 0xD7A4)) + string.ascii_letters + string.digits + punct + " ")
    allowed = "\u266a"
    for ch in content:
        if ch in allowed:
            continue
        if ch not in ansi:
            return True
        if ch == "/":
            return True
    return False


def validate_sync_negative_or_zero(start_time: timedelta, end_time: timedelta, **kwargs) -> bool:
    return start_time >= end_time


def validate_ellipsis_count(content: str, criterion: int = 2, **kwargs) -> bool:
    content = content.replace("\n", " ")
    for m in re.findall(r"\.{2,}", content):
        if len(m) == criterion:
            return True
    return False


# ============================================================
# 2차 후처리 (postprocess_stage2)
# ============================================================

def postprocess_merge_overlapped_sync(subs: List[srt.Subtitle], max_lines_per_sub: int = 1, **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs

    def _ok(t):
        return t is not None and t.strip().count("\n") < max_lines_per_sub

    subs = sorted(subs, key=lambda x: (x.start, x.end))
    result = []
    i, n = 0, len(subs)
    while i < n:
        cur = subs[i]
        if i == n - 1:
            result.append(cur); break
        nxt = subs[i + 1]
        if (cur.end > nxt.start) and _ok(cur.content) and _ok(nxt.content):
            merged = srt.Subtitle(index=cur.index, start=cur.start, end=max(cur.end, nxt.end), content=f"{cur.content}\n{nxt.content}")
            set_origin_indices(merged, get_origin_indices(cur) + get_origin_indices(nxt))
            result.append(merged); i += 2
        else:
            result.append(cur); i += 1
    return postprocess_reset_subtitles_from_list(result)


def postprocess_remove_not_pair_characters(content: str, pair_char: Optional[Dict[str, str]] = None, **kwargs) -> str:
    if content is None:
        return ""
    if pair_char is None:
        pair_char = {"(": ")", "[": "]", '"': '"', "'": "'", "<": ">", "\u266a": "\u266a"}
    flat = replace_linebreak(content)
    text = content
    for o, c in pair_char.items():
        oc, cc = flat.count(o), flat.count(c)
        if o == c:
            if oc % 2 != 0:
                text = text.replace(o, "")
            continue
        if oc != cc:
            text = text.replace(o, "").replace(c, "")
    return text


def postprocess_remove_mid_period(sentence: str, **kwargs) -> str:
    if sentence is None:
        return ""
    out = []
    for line in sentence.splitlines():
        kept = []

        def _keep(m):
            kept.append(m.group(0))
            return f"\ue000{len(kept) - 1}\ue001"
        line = re.sub(r"\.{3,}", _keep, line)
        line = re.sub(r"\.\.", _keep, line)
        line = re.sub(r"(?<!\d)\.(?!\d)(?!\s*$)", "", line)
        line = re.sub(r"\ue000(\d+)\ue001", lambda m: kept[int(m.group(1))], line)
        out.append(line)
    return "\n".join(out)


def _split_line_half(line: str) -> str:
    mid = len(line) // 2
    best, best_dist = -1, len(line)
    for idx, ch in enumerate(line):
        if ch == " ":
            d = abs(idx - mid)
            if d < best_dist:
                best_dist = d; best = idx
    if best >= 0:
        return line[:best] + "\n" + line[best + 1:]
    return line[:mid] + "\n" + line[mid:]


def postprocess_add_period_between_subs(subs: List[srt.Subtitle], ending_punctuation: str = ".!?~", max_chars_per_line: int = 17, max_lines: int = 3, **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs
    for i in range(len(subs) - 1):
        cur, nxt = subs[i], subs[i + 1]
        if not cur.content or not nxt.content:
            continue
        first = nxt.content.splitlines()[0].strip()
        if not (first.startswith("-") or first.startswith("(")):
            continue
        cl = cur.content.splitlines()
        last = cl[-1].rstrip()
        if not last or last.endswith("...") or last[-1] in ending_punctuation or last[-1] in ")]":
            continue
        cl[-1] = last + "."
        if len(strip_style_tags(cl[-1])) > max_chars_per_line and len(cl) < max_lines:
            cl[-1] = _split_line_half(cl[-1])
        cur.content = "\n".join(cl)
    return subs


def postprocess_add_period_between_lines(sentence: str, ending_punctuation: str = ".!?~", max_chars_per_line: int = 17, max_lines: int = 3, **kwargs) -> str:
    if sentence is None:
        return ""
    lines = sentence.splitlines()
    if len(lines) < 2:
        return sentence
    for i in range(len(lines) - 1):
        cur = lines[i].rstrip()
        nxt = lines[i + 1].strip()
        if not cur or not nxt or not (nxt.startswith("-") or nxt.startswith("(")):
            continue
        if cur.endswith("...") or cur[-1] in ending_punctuation or cur[-1] in ")]":
            continue
        cur = cur + "."
        if len(strip_style_tags(cur)) > max_chars_per_line and len(lines) < max_lines:
            parts = _split_line_half(cur).split("\n")
            lines[i] = parts[0]; lines.insert(i + 1, parts[1])
        else:
            lines[i] = cur
    return "\n".join(lines)


def postprocess_remove_oc_check(text, **kwargs):
    return re.sub(r"\^", "", text) if text else ""


def postprocess_remove_double_quotation_mark(text, **kwargs):
    return re.sub(r'"', "", text) if text else ""


def postprocess_remove_star(text, **kwargs):
    return re.sub(r"\*", "", text) if text else ""


def postprocess_remove_music_notes(text, **kwargs):
    return re.sub(r"[\u266a\u266b]", "", text) if text else ""


def postprocess_remove_square_brackets(text, **kwargs):
    return re.sub(r"[\[\]]", "", text) if text else ""


def postprocess_remove_parentheses(text, **kwargs):
    return re.sub(r"[\(\)]", "", text) if text else ""


def postprocess_remove_angle_brackets(text, **kwargs):
    return re.sub(r"[<>]", "", text) if text else ""


def postprocess_remove_other_characters(text, **kwargs):
    if text is None:
        return ""
    o = text
    o = postprocess_remove_star(o); o = postprocess_remove_music_notes(o)
    o = postprocess_remove_square_brackets(o); o = postprocess_remove_parentheses(o)
    o = postprocess_remove_angle_brackets(o); o = postprocess_remove_oc_check(o)
    return o


def postprocess_normalize_asterisk_for_skbb(sentence: str, **kwargs) -> str:
    def _r(m):
        c = len(m.group(0))
        if c > 2:
            return "**"
        if c == 2:
            return "**"
        return "asterisks"
    result = re.sub(r"\*{2,}", _r, sentence)
    return re.sub(r"\s+$", "", result)


def postprocess_remove_star_and_angle_for_skbb(text, **kwargs):
    if text is None:
        return ""
    t = postprocess_remove_double_quotation_mark(text)
    t = postprocess_remove_music_notes(t)
    t = postprocess_remove_parentheses(t)
    t = postprocess_remove_angle_brackets(t)
    return t


def postprocess_remove_not_pair_paren_quotes_for_skbb(text, **kwargs):
    if text is None:
        return ""
    return postprocess_remove_not_pair_characters(text, pair_char={"'": "'", "<": ">"})


def postprocess_remove_first_hypn(sentence: str, punctuation: Optional[str] = None, **kwargs) -> str:
    if not sentence:
        return sentence
    si = kwargs.get("subtitle_index", None)
    if si is None or si != 1:
        return sentence
    if punctuation is None:
        punctuation = "-"
    i, n = 0, len(sentence)
    while i < n and sentence[i].isspace():
        i += 1
    if i < n and sentence[i] in punctuation:
        return sentence[:i] + sentence[i + 1:]
    return sentence


def postprocess_keep_bracket_music_note_and_remove_others_for_lghv(text, **kwargs):
    if text is None:
        return ""
    S = "\ue000"
    o = re.sub(r"\[\u266b\s*", "[\u266b ", text)
    o = o.replace("[\u266b ", f"[{S} ")
    o = re.sub(r"[\u266b]", "", o)
    o = o.replace(f"[{S} ", "[\u266b ")
    return o


def postprocess_remove_star_and_angle_for_lghv(text, **kwargs):
    if text is None:
        return ""
    return postprocess_remove_angle_brackets(postprocess_remove_star(text))


def postprocess_remove_not_pair_paren_quotes_for_lghv(text, **kwargs):
    if text is None:
        return ""
    return postprocess_remove_not_pair_characters(text, pair_char={"(": ")", '"': '"', "'": "'"})


def postprocess_normalize_music_to_double_note_for_lghv(text, **kwargs):
    if text is None:
        return ""
    return re.sub(r"[\u2669\u266a\u266b\u266c\u266d\u266e\u266f]", "\u266b", text)


def postprocess_normalize_music_to_single_note_for_tvng(text, **kwargs):
    if text is None:
        return ""
    return re.sub(r"[\u2669\u266a\u266b\u266c\u266d\u266e\u266f]", "\u266a", text)


def postprocess_apply_overlap_hyphen_for_all_speech(subs: List[srt.Subtitle], dash_prefix: str = "- ", **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs
    ordered = sorted(subs, key=lambda x: (x.start, x.end, x.index))

    def _nz(c):
        return sum(1 for l in (c or "").splitlines() if l.strip())

    def _is_sound(c):
        lines = [l.strip() for l in (c or "").splitlines() if l.strip()]

        def _s(l):
            if not (l.startswith("[") and l.endswith("]")):
                return False
            return l not in ("[\uc601\uc5b4]", "[\uc77c\ubcf8\uc5b4]", "[\uc911\uad6d\uc5b4]", "[\uc678\uad6d\uc5b4]")
        return bool(lines) and all(_s(l) for l in lines)

    def _speech(s):
        return not _is_sound(s.content or "")

    def _dash(c):
        out = []
        for line in (c or "").splitlines():
            if not line.strip():
                out.append(line); continue
            m = re.match(r"^(\s*)(.*)$", line)
            ind, core = m.group(1), m.group(2)
            out.append(line if core.startswith(dash_prefix) else f"{ind}{dash_prefix}{core}")
        return "\n".join(out)

    out, n, i = [], len(ordered), 0
    while i < n:
        group = [ordered[i]]; gend = ordered[i].end; j = i + 1
        while j < n:
            if ordered[j].start < gend:
                group.append(ordered[j]); gend = max(gend, ordered[j].end); j += 1
            else:
                break
        if len(group) <= 1:
            out.extend(group); i = j; continue
        sound = any(not _speech(s) for s in group)
        total = sum(_nz(s.content or "") for s in group)
        speech_cnt = sum(1 for s in group if _speech(s))
        limit = 3 if sound else 2
        if not (total <= limit and speech_cnt >= 2):
            out.extend(group); i = j; continue
        for s in group:
            if not _speech(s):
                out.append(s); continue
            ns = srt.Subtitle(index=s.index, start=s.start, end=s.end, content=_dash(s.content or ""), proprietary=s.proprietary)
            set_origin_indices(ns, get_origin_indices(s))
            out.append(ns)
        i = j
    return sorted(out, key=lambda x: (x.start, x.end, x.index))


def postprocess_over_length_lines(text: str, max_length: int = 18, **kwargs) -> str:
    if text is None:
        return ""
    out = []
    for line in text.splitlines():
        if not line or len(strip_style_tags(line)) <= max_length:
            out.append(line); continue
        words = line.split()
        cur, wrapped = "", []
        for w in words:
            cand = w if not cur else cur + " " + w
            if len(strip_style_tags(cand)) > max_length and cur:
                wrapped.append(cur); cur = w
            else:
                cur = cand
        if cur:
            wrapped.append(cur)
        out.extend(wrapped)
    return "\n".join(out)


def postprocess_mark_overlapped_multi_speaker(subs: List[srt.Subtitle], reassign_index: bool = True, multi_speaker_prefix: str = "- ", max_lines_per_sub: int = 1, multi_overlap_strategy: str = "best_pair", max_merged_lines: int = 2, **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs

    def _ok(t):
        return t is not None and t.strip().count("\n") < max_lines_per_sub

    def _dash(line):
        if line is None:
            return ""
        s = line.strip()
        if not multi_speaker_prefix:
            return s
        return s if s.startswith(multi_speaker_prefix) else f"{multi_speaker_prefix}{s}"

    def _bracket(t):
        if t is None:
            return False
        s = t.strip()
        return s.startswith("[") and s.endswith("]") and len(s) > 2

    ordered = sorted(subs, key=lambda x: (x.start, x.end))
    first_idx = ordered[0].index if ordered else None
    result = []
    n, i = len(ordered), 0
    no_merge = set()
    while i < n:
        group = [ordered[i]]; gend = ordered[i].end; j = i + 1
        while j < n:
            if ordered[j].start < gend:
                group.append(ordered[j])
                if ordered[j].end > gend:
                    gend = ordered[j].end
                j += 1
            else:
                break
        if len(group) == 1:
            result.append(group[0])
        else:
            has_b = any(_ok(s.content) and _bracket(s.content) for s in group)
            if has_b and multi_overlap_strategy != "merge_all":
                for s in group:
                    no_merge.add(s.index)
                result.extend(group)
            elif not all(_ok(s.content) for s in group):
                result.extend(group)
            elif len(group) == 2:
                g0, g1 = group
                n0 = srt.Subtitle(index=g0.index, start=g0.start, end=g0.end, content=_dash(g0.content) if g0.index != first_idx else g0.content)
                set_origin_indices(n0, get_origin_indices(g0))
                n1 = srt.Subtitle(index=g1.index, start=g1.start, end=g1.end, content=_dash(g1.content) if g1.index != first_idx else g1.content)
                set_origin_indices(n1, get_origin_indices(g1))
                result.extend([n0, n1])
            else:
                result.extend(group)
        i = j

    cand = [s for s in result if s.index not in no_merge]
    non = [s for s in result if s.index in no_merge]
    cand = sorted(cand, key=lambda x: (x.start, x.end, x.index))
    merged = []
    m, k = len(cand), 0
    while k < m:
        g = [cand[k]]; gend = cand[k].end; t = k + 1
        while t < m:
            if cand[t].start < gend:
                g.append(cand[t])
                if cand[t].end > gend:
                    gend = cand[t].end
                t += 1
            else:
                break
        if len(g) <= 2:
            total = sum(s.content.strip().count("\n") + 1 for s in g if s.content)
            if total <= max_merged_lines:
                merged.extend(postprocess_merge_overlapped_sync(g, max_lines_per_sub=max_lines_per_sub))
            else:
                merged.extend(g)
        else:
            total = sum(s.content.strip().count("\n") + 1 for s in g if s.content)
            allok = all(_ok(s.content) for s in g)
            if multi_overlap_strategy == "merge_all":
                if allok and total <= max_merged_lines:
                    gd = []
                    for s in g:
                        nc = s.content if s.index == first_idx else _dash(s.content)
                        ns = srt.Subtitle(index=s.index, start=s.start, end=s.end, content=nc)
                        set_origin_indices(ns, get_origin_indices(s))
                        gd.append(ns)
                    mr = gd
                    while True:
                        pl = len(mr)
                        mr = postprocess_merge_overlapped_sync(mr, max_lines_per_sub=max_merged_lines)
                        if len(mr) >= pl:
                            break
                    merged.extend(mr)
                else:
                    merged.extend(g)
            else:
                best, bo = None, timedelta(0)
                for a in range(len(g)):
                    for b in range(a + 1, len(g)):
                        s1, s2 = g[a], g[b]
                        ov = min(s1.end, s2.end) - max(s1.start, s2.start)
                        if ov > bo:
                            bo, best = ov, (a, b)
                if best is None or bo <= timedelta(0):
                    merged.extend(g)
                else:
                    i1, i2 = best
                    if i1 > i2:
                        i1, i2 = i2, i1
                    gwd = []
                    for idx, s in enumerate(g):
                        if idx in (i1, i2):
                            nc = s.content if s.index == first_idx else _dash(s.content)
                            ns = srt.Subtitle(index=s.index, start=s.start, end=s.end, content=nc)
                            set_origin_indices(ns, get_origin_indices(s))
                            gwd.append(ns)
                        else:
                            gwd.append(s)
                    pair = [gwd[i1], gwd[i2]]
                    mp = postprocess_merge_overlapped_sync(pair, max_lines_per_sub=max_lines_per_sub)
                    go = []
                    if len(mp) == 1:
                        ms = mp[0]
                        others = [s for idx, s in enumerate(gwd) if idx not in (i1, i2)]
                        for io, other in enumerate(others):
                            if not _ok(other.content):
                                continue
                            os_, oe = max(ms.start, other.start), min(ms.end, other.end)
                            if oe <= os_:
                                continue
                            mid = os_ + (oe - os_) / 2
                            if ms.start <= other.start:
                                nm = srt.Subtitle(index=ms.index, start=ms.start, end=mid, content=ms.content)
                                set_origin_indices(nm, get_origin_indices(ms))
                                no_ = srt.Subtitle(index=other.index, start=mid, end=other.end, content=other.content)
                                set_origin_indices(no_, get_origin_indices(other))
                            else:
                                no_ = srt.Subtitle(index=other.index, start=other.start, end=mid, content=other.content)
                                set_origin_indices(no_, get_origin_indices(other))
                                nm = srt.Subtitle(index=ms.index, start=mid, end=ms.end, content=ms.content)
                                set_origin_indices(nm, get_origin_indices(ms))
                            ms = nm; others[io] = no_; break
                        go.extend(others); go.append(ms)
                    else:
                        go.extend(gwd)
                    merged.extend(sorted(go, key=lambda x: (x.start, x.end, x.index)))
        k = t

    final = sorted(merged + non, key=lambda x: (x.start, x.end, x.index))
    for i in range(len(final) - 1):
        final[i].end = postprocess_sync_overlap(final[i].end, final[i + 1].start)
    if reassign_index:
        return postprocess_reset_subtitles_from_list(final)
    return final


def postprocess_adjust_short_sync(subs: List[srt.Subtitle], min_duration_sec: float = 1.0, gap_sec: float = 0.083, **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs
    min_gap = timedelta(seconds=gap_sec)
    min_dur = timedelta(seconds=min_duration_sec)
    ps = sorted(list(subs), key=lambda x: (x.start, x.end))
    for i, sub in enumerate(ps):
        if sub.end - sub.start >= min_dur:
            continue
        target = sub.start + min_dur
        nxt = ps[i + 1] if i < len(ps) - 1 else None
        if nxt is None:
            sub.end = target; continue
        max_end = nxt.start - min_gap
        if target <= max_end:
            sub.end = target
        elif max_end > sub.end:
            sub.end = max_end
    return ps


def postprocess_merge_gap_subs(subs: List[srt.Subtitle], gap_sec: float = 0.083, max_lines_after_merge: int = 3, max_chars_per_line: int = 17, max_gap_sec: float = 0.4, **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs
    ending = ".!?~"
    gap_td = timedelta(seconds=gap_sec)
    ps = sorted(list(subs), key=lambda x: (x.start, x.end))
    for sub in ps:
        if not hasattr(sub, "_origin_indices"):
            set_origin_indices(sub, [sub.index])

    def _ov(a, b):
        return a.start < b.end and b.start < a.end

    def _has_ov(idx):
        t = ps[idx]
        for j in range(idx - 1, -1, -1):
            if _ov(t, ps[j]):
                return True
        for j in range(idx + 1, len(ps)):
            if ps[j].start >= t.end:
                break
            if _ov(t, ps[j]):
                return True
        return False

    def _can(last, first):
        last = last.rstrip(); first = first.strip()
        if not last or not first or last.endswith("...") or last[-1] in ending:
            return False
        if first.startswith("-") or first.startswith("(") or last[-1] in ")":
            return False
        return True

    def _try(front, back):
        fl = front.content.splitlines() if front.content else []
        bl = back.content.splitlines() if back.content else []
        if not fl or not bl:
            return False
        if _can(fl[-1], bl[0]):
            ml = fl[-1].rstrip() + " " + bl[0].strip()
            if len(strip_style_tags(ml)) <= max_chars_per_line:
                if len(fl) + len(bl) - 1 <= max_lines_after_merge:
                    fl[-1] = ml
                    rem = bl[1:]
                    front.content = "\n".join(fl) + ("\n" + "\n".join(rem) if rem else "")
                    front.end = max(front.end, back.end)
                    set_origin_indices(front, get_origin_indices(front) + get_origin_indices(back))
                    return True
        if len(fl) + len(bl) <= max_lines_after_merge:
            fc = front.content.strip() if front.content else ""
            bc = back.content.strip() if back.content else ""
            front.content = f"{fc}\n{bc}" if fc and bc else (fc or bc)
            front.end = max(front.end, back.end)
            set_origin_indices(front, get_origin_indices(front) + get_origin_indices(back))
            return True
        return False

    i = 0
    while i < len(ps):
        if i >= len(ps) - 1:
            break
        cur, nxt = ps[i], ps[i + 1]
        if (nxt.start - cur.end) != gap_td:
            i += 1; continue
        if _has_ov(i) or _has_ov(i + 1):
            i += 1; continue
        if _try(cur, nxt):
            ps.pop(i + 1); continue
        if i > 0:
            prev = ps[i - 1]
            if (cur.start - prev.end).total_seconds() <= max_gap_sec:
                if _has_ov(i - 1) or _has_ov(i):
                    i += 1; continue
                if _try(prev, cur):
                    ps.pop(i); i = max(i - 1, 0); continue
        i += 1
    for ni, sub in enumerate(ps, start=1):
        sub.index = ni
    return ps


def postprocess_adjust_subtitle_gaps(subs: List[srt.Subtitle], gap_sec: float = 0.083, **kwargs) -> List[srt.Subtitle]:
    if not subs:
        return subs
    min_gap = timedelta(seconds=gap_sec)
    zero = timedelta(0)
    subs = sorted(subs, key=lambda x: (x.start, x.end))
    result = []
    gmax = subs[0].end
    for i, cur in enumerate(subs):
        gmax = cur.end if cur.start >= gmax else max(gmax, cur.end)
        if i < len(subs) - 1:
            nxt = subs[i + 1]
            cg = nxt.start - cur.end
            eg = nxt.start - gmax
            if zero <= cg and zero <= eg < min_gap:
                origin = get_origin_indices(cur)
                cur = srt.Subtitle(index=cur.index, start=cur.start, end=nxt.start - min_gap, content=cur.content, proprietary=cur.proprietary)
                set_origin_indices(cur, origin)
        result.append(cur)
    return postprocess_reset_subtitles_from_list(result)


def postprocess_remove_space_after_hypn(sentence: str, **kwargs) -> str:
    if sentence is None:
        return ""
    out = []
    for line in sentence.splitlines():
        s = line.lstrip()
        if s.startswith("- "):
            s = "-" + s[2:]
        out.append(s)
    return "\n".join(out)


# ============================================================
# 최종 납품 (postprocess_final)
# ============================================================

def postprocess_add_banner_subtitle(subtitles: List[srt.Subtitle], banner_sentence: str = "", banner_start: str = "00:00:00,000", banner_end: str = "00:05:00,000", **kwargs) -> List[srt.Subtitle]:
    if not subtitles:
        return subtitles
    banner = srt.Subtitle(index=0, start=parse_srt_time(banner_start), end=parse_srt_time(banner_end), content=banner_sentence)
    result = [banner] + subtitles
    rs = sorted(result, key=lambda s: (s.start, s.end))
    for ni, sub in enumerate(rs, start=1):
        sub.index = ni
    return rs


def postprocess_remove_last_punctuation(sentence: str, punctuation: List[str] = None, **kwargs) -> str:
    if sentence is None:
        return ""
    if punctuation is None:
        punctuation = ["."]
    out = []
    for line in sentence.splitlines():
        s = line.rstrip()
        if not s:
            out.append(line); continue
        result = []
        i = 0
        while i < len(s):
            ch = s[i]
            if ch in punctuation:
                if ch == "." and i + 1 < len(s) and s[i + 1] == ".":
                    while i < len(s) and s[i] == ".":
                        result.append(s[i]); i += 1
                    continue
                prev = s[i - 1] if i > 0 else ""
                nxt = s[i + 1] if i + 1 < len(s) else ""
                if prev.isdigit() and nxt.isdigit():
                    result.append(ch); i += 1; continue
                if prev.isascii() and prev.isalpha() and nxt.isascii() and nxt.isalpha():
                    result.append(ch); i += 1; continue
                i += 1; continue
            result.append(ch); i += 1
        out.append("".join(result))
    return "\n".join(out)


# ============================================================
# 2차 검증 (validate_stage2)
# ============================================================

def validate_special_characters(content: str, **kwargs) -> bool:
    content = replace_linebreak(content)
    ansi = ("".join(chr(i) for i in range(0xAC00, 0xD7A4)) + string.ascii_letters + string.digits + string.punctuation + " ")
    for ch in content:
        if ch not in ansi:
            return True
    return False


def validate_overlapped_over_lines(front_content: str, back_content: str, front_end_time: timedelta, back_start_time: timedelta, max_lines: int = 2, **kwargs) -> bool:
    if front_end_time <= back_start_time:
        return False

    def _lc(t):
        return 0 if not t or not t.strip() else t.count("\n") + 1
    return _lc(front_content) >= max_lines or _lc(back_content) >= max_lines


def validate_hyphen_no_space_after_for_skbb(content: str, **kwargs) -> bool:
    if not content:
        return False
    for line in content.splitlines():
        s = line.lstrip()
        if not s.startswith("-"):
            continue
        if len(s) == 1:
            continue
        if s[1].isspace():
            return True
    return False


def validate_mosaic_count_for_skbb(content: str, criterion: int = 2, **kwargs) -> bool:
    if not content:
        return False
    groups = re.findall(r"\*+", content)
    if not groups:
        return False
    for g in groups:
        if len(g) != criterion:
            return True
    return False


def validate_sync_overlapped(front_content: str, back_content: str, front_end_time: timedelta, back_start_time: timedelta, **kwargs) -> bool:
    if front_end_time is None or back_start_time is None:
        return False
    return front_end_time > back_start_time


def validate_overlapped_only_text_for_lghv(front_content: str, back_content: str, front_end_time: timedelta, back_start_time: timedelta, **kwargs) -> bool:
    if front_end_time <= back_start_time:
        return False

    def _single(t):
        return t is not None and "\n" not in t.strip()

    def _bonly(t):
        if t is None:
            return False
        s = t.strip()
        if not s or not (s.startswith("[") and s.endswith("]")):
            return False
        return bool(s[1:-1].strip())
    if not (_single(front_content) and _single(back_content)):
        return False
    return _bonly(front_content) or _bonly(back_content)


def validate_overlapped_accumulated_lines(subtitles: List[srt.Subtitle], max_lines: int = 3, **kwargs) -> Dict[int, str]:
    if not subtitles:
        return {}
    ordered = sorted(subtitles, key=lambda x: (x.start, x.end, x.index))
    errors: Dict[int, str] = {}

    def _lc(t):
        return 0 if not t or not t.strip() else t.count("\n") + 1

    def _flush(group):
        if len(group) < 2:
            return
        total = sum(_lc(s.content) for s in group)
        if total <= max_lines:
            return
        idxs = [s.index for s in group]
        detail = f"\uc5f0\uc18d \uc624\ubc84\ub7a9 \uad6c\uac04 #{', #'.join(map(str, idxs))} \ucd1d {total}\uc904 ({max_lines}\uc904 \ucd08\uacfc)"
        for s in group:
            errors[s.index] = detail

    cur, cend = [], None
    for sub in ordered:
        if not cur:
            cur = [sub]; cend = sub.end; continue
        if sub.start < cend:
            cur.append(sub)
            if sub.end > cend:
                cend = sub.end
        else:
            _flush(cur); cur = [sub]; cend = sub.end
    _flush(cur)
    return errors


def validate_sync_short_duration(start_time: timedelta, end_time: timedelta, min_duration_sec: float = 1.0, **kwargs) -> bool:
    if start_time is None or end_time is None:
        return False
    return 0 < (end_time - start_time).total_seconds() < min_duration_sec


def validate_comma_space(content: str, **kwargs) -> bool:
    if not content:
        return False
    n = len(content)
    for i, ch in enumerate(content):
        if ch != ",":
            continue
        if i == n - 1:
            continue
        prev_d = i > 0 and content[i - 1].isdigit()
        next_d = (i + 1 < n) and content[i + 1].isdigit()
        if prev_d and next_d:
            continue
        prev_sp = (i == 0) or content[i - 1].isspace()
        next_sp = content[i + 1].isspace()
        if not prev_sp and not next_sp:
            return True
    return False