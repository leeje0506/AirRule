#!/usr/bin/env python3
"""imbc playvod 전체 회차 자막 내려받기 (vtt + srt).

사용: python3 imbc_caption.py <프로그램명 | bid | progCode> [저장폴더]
저장: {저장폴더}/{프로그램명}/vtt/{프로그램명}_{회차}.vtt
      {저장폴더}/{프로그램명}/srt/{프로그램명}_{회차}.srt
통합본 분할: python3 imbc_caption.py --split '<프로그램폴더>' [boundaries.json]
자체 점검: python3 imbc_caption.py --test
"""
import json, re, sys, urllib.parse, urllib.request
from pathlib import Path

API = "https://playvod.imbc.com/api/ContentList_Templete?programId={}&orderBy=d&selectYear=0&curPage={}&pageSize=100"
SEARCH = "https://cue.imbc.com/api/program.aspx?query={}&startNum=0"
VTT = "https://playvod.imbc.com/caption/{}/caption_{}.vtt"
HDR = {"User-Agent": "Mozilla/5.0", "Referer": "https://playvod.imbc.com/"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read()


def _safe(t):
    return re.sub(r'[/\\:*?"<>|]', "_", t).strip()


def _norm(t):
    return re.sub(r"\s+", "", t)


def search(name):
    """프로그램명 -> [(progCode, title)], 제목 일치도순."""
    # ponytail: startNum 은 0-베이스. 동명 프로그램은 제목 일치순으로만 거름 — 애매하면 progCode 직접 입력
    data = json.loads(get(SEARCH.format(urllib.parse.quote(name))))
    hits = {p["ProgramCode"]: re.sub(r"<[^>]+>", "", p["ProgramTitle"])
            for p in data.get("nProgramList") or []}
    want = _norm(name)
    return sorted(hits.items(), key=lambda h: (_norm(h[1]) != want,
                                               not _norm(h[1]).startswith(want),
                                               want not in _norm(h[1]),
                                               len(h[1])))


def resolve(arg):
    """bid / progCode / 프로그램명 어느 쪽이든 progCode 로."""
    if not arg.isdigit():
        hits = search(arg)
        if not hits or _norm(arg) not in _norm(hits[0][1]):
            print(f"'{arg}' 로 딱 맞는 프로그램을 못 찾음." + (" 후보:" if hits else ""))
            for code, title in hits[:10]:
                print(f"  {code}  {title}")
            sys.exit(1)
        code, title = hits[0]
        if len(hits) > 1 and _norm(title) != _norm(arg):
            print("다른 후보:", ", ".join(f"{t}({c})" for c, t in hits[1:6]))
        print(f"찾음: {title} ({code})")
        return code
    page = get(f"https://playvod.imbc.com/Templete/VodView?bid={arg}").decode("utf-8", "replace")
    m = re.search(r"progCode=(\d+)", page)
    return m.group(1) if m else arg


def _sec(ts):
    """'00:01:02.250' / '01:02,250' -> 초(float)."""
    bits = ts.strip().replace(",", ".").split(":")
    h = float(bits[0]) if len(bits) == 3 else 0.0
    return h * 3600 + float(bits[-2]) * 60 + float(bits[-1])


def _fmt(t, sep="."):
    """초 -> 'HH:MM:SS.mmm' (sep=',' 이면 SRT 형식)."""
    h, rem = divmod(max(t, 0.0), 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}".replace(".", sep)


def parse_vtt(text):
    """WebVTT -> (시작초, 끝초, 본문줄들) 순회. 헤더/주석/큐ID/큐설정은 버림."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    for block in re.split(r"\n{2,}", text.strip()):
        lines = block.split("\n")
        if lines[0].startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        i = next((j for j, l in enumerate(lines) if "-->" in l), None)
        if i is None:
            continue
        start, _, rest = lines[i].partition("-->")
        parts = rest.split()  # 뒤에 붙는 큐 설정(align/position/line)은 버림
        body = [l.rstrip() for l in lines[i + 1:] if l.strip()]
        if parts and body:
            yield _sec(start), _sec(parts[0]), body


def vtt_to_srt(text):
    """WebVTT -> SRT. VTT 전용 태그만 제거하고 i/b/u 는 유지, 순번은 1부터."""
    out = []
    for start, end, body in parse_vtt(text):
        body = [l for l in (re.sub(r"<(?!/?[ibu]>)[^>]*>", "", l).rstrip() for l in body) if l.strip()]
        if not body:
            continue
        out.append(f"{len(out) + 1}\n{_fmt(start, ',')} --> {_fmt(end, ',')}\n" + "\n".join(body))
    return "\n\n".join(out) + "\n"


def write_vtt(cues):
    return "WEBVTT\n\n" + "\n\n".join(
        f"{_fmt(s)} --> {_fmt(e)}\n" + "\n".join(body) for s, e, body in cues) + "\n"


def split_program(folder, boundaries=None):
    """통합본(001-002)을 1부 영상 길이 기준으로 쪼개서 각 회차 파일 생성."""
    folder = Path(folder)
    bfile = Path(boundaries) if boundaries else folder / "boundaries.json"
    if not bfile.exists():
        sys.exit(f'경계 파일 없음: {bfile}\n형식: {{"001-002": "00:31:05.120"}}  (값 = 1부 영상 길이)')
    for key, cut in json.loads(bfile.read_text(encoding="utf-8")).items():
        if not cut:
            print("경계 미입력", key); continue
        src = next(folder.glob(f"vtt/*_{key}.vtt"), None)
        if src is None:
            print("원본 없음", key); continue
        cut = _sec(cut)
        first, second = [], []
        for start, end, body in parse_vtt(src.read_text(encoding="utf-8-sig")):
            if start < cut:
                first.append((start, end, body))                 # 시작 기준 배치 — 걸친 큐는 1부에 통째로
            else:
                second.append((start - cut, end - cut, body))    # 2부는 1부 길이만큼 당김
        stem = src.stem[:-len(key)]
        for part, cues in zip(key.split("-"), (first, second)):
            if not cues:
                print("빈 구간", key, part); continue
            vtt = write_vtt(cues)
            (folder / "vtt" / f"{stem}{part}.vtt").write_text(vtt, encoding="utf-8")
            (folder / "srt" / f"{stem}{part}.srt").write_text(vtt_to_srt(vtt), encoding="utf-8")
        a, b = key.split("-")
        print(f"{key} -> {a}({len(first)}큐) + {b}({len(second)}큐)")


def episodes(pid):
    page = 1
    while True:
        data = json.loads(get(API.format(pid, page)))
        yield from data["ContList"]
        if page * 100 >= data["TotalCount"]:
            return
        page += 1


def main(bid, outdir="captions"):
    pid = resolve(bid)
    for ep in episodes(pid):
        title = _safe(ep["ProgramTitle"])
        num = _safe(re.sub(r"\d+", lambda m: m.group().zfill(3),
                           (ep["ContentNumber"] or ep["BroadDate"]).strip()))
        base, name = Path(outdir) / title, f"{title}_{num}"
        vtt_path, srt_path = base / "vtt" / f"{name}.vtt", base / "srt" / f"{name}.srt"
        if vtt_path.exists() and srt_path.exists():
            continue
        if ep["CaptionYN"] != "Y":
            print("자막없음", name); continue
        try:
            for path in (vtt_path, srt_path):
                path.parent.mkdir(parents=True, exist_ok=True)
            raw = get(VTT.format(pid, ep["ContentId"])).decode("utf-8-sig", "replace")
            vtt_path.write_text(raw, encoding="utf-8")
            srt_path.write_text(vtt_to_srt(raw), encoding="utf-8")
            print("저장", name)
        except Exception as e:
            print("실패", name, e)


def test():
    src = ("\ufeffWEBVTT\n\nNOTE 주석 블록\n\n"
           "cue-1\n00:00:10.498 --> 00:00:15.728 align:start position:0%\n"
           "<v 화자>첫 줄</v>\n<i>둘째 줄</i>\n\n"
           "01:02.250 --> 01:04.000\n짧은 형식\n\n"
           "00:00:20.000 --> 00:00:21.000\n\n")  # 본문 없는 큐는 버림
    got = vtt_to_srt(src)
    assert got == ("1\n00:00:10,498 --> 00:00:15,728\n첫 줄\n<i>둘째 줄</i>\n\n"
                   "2\n00:01:02,250 --> 00:01:04,000\n짧은 형식\n"), repr(got)
    assert _sec("00:01:02.500") == 62.5 and _sec("01:02,500") == 62.5
    assert _fmt(62.5) == "00:01:02.500" and _fmt(62.5, ",") == "00:01:02,500"
    assert _safe("a/b:c") == "a_b_c"

    # 분할: 경계 100초. 90~110 큐는 1부에서 100 으로 잘리고, 2부는 0 부터 재시작
    cues = list(parse_vtt("WEBVTT\n\n00:00:10.000 --> 00:00:12.000\n가\n\n"
                          "00:01:30.000 --> 00:01:50.000\n나\n\n"
                          "00:02:00.000 --> 00:02:05.000\n다\n"))
    cut = 100.0
    first = [(s_, e, b) for s_, e, b in cues if s_ < cut]
    second = [(s_ - cut, e - cut, b) for s_, e, b in cues if s_ >= cut]
    assert [(_fmt(a), _fmt(b)) for a, b, _ in first] == [
        ("00:00:10.000", "00:00:12.000"), ("00:01:30.000", "00:01:50.000")]
    assert [(_fmt(a), _fmt(b)) for a, b, _ in second] == [("00:00:20.000", "00:00:25.000")]
    assert vtt_to_srt(write_vtt(second)).startswith("1\n00:00:20,000 --> 00:00:25,000\n다")
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--test"]:
        test()
    elif sys.argv[1:2] == ["--split"]:
        split_program(*sys.argv[2:])
    else:
        main(*sys.argv[1:])
