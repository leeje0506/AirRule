#!/usr/bin/env python3
"""JTBC 다시보기 전체 회차 자막 내려받기 (vtt + srt).

사용: python3 jtbc_caption.py [-o 저장폴더(기본 docs/JTBC)] <프로그램명> [프로그램명 ...]
저장: {저장폴더}/{프로그램명}/vtt/{프로그램명}_{회차}.vtt
      {저장폴더}/{프로그램명}/srt/{프로그램명}_{회차}.srt
"""
import json, re, sys, urllib.parse, urllib.request
from pathlib import Path

from imbc_caption import _safe, vtt_to_srt  # SRT 변환은 MBC 스크립트와 공유

TV = "https://tv.jtbc.co.kr"
HDR = {"User-Agent": "Mozilla/5.0", "Origin": TV, "Referer": TV + "/"}


def _cookie():
    """19세 회차용 로그인 쿠키: 환경변수 JTBC_COOKIE 또는 저장소 루트 .env 의 JTBC_COOKIE=..."""
    import os
    if os.environ.get("JTBC_COOKIE"):
        return os.environ["JTBC_COOKIE"]
    root = Path(__file__).resolve().parents[3]   # 저장소 루트
    for env in (root / ".env", root / "backend" / ".env"):
        for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
            if line.startswith("JTBC_COOKIE="):
                return line.partition("=")[2].strip().strip("'\"")



def get(url, data=None, cookie=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    hdr = {**HDR, "Cookie": cookie} if cookie else HDR
    return urllib.request.urlopen(urllib.request.Request(url, body, hdr), timeout=30).read().decode("utf-8-sig", "replace")


def _norm(t):
    """공백·문장부호·[무삭제판] 같은 머리말 무시하고 비교."""
    return re.sub(r"[\W_]+", "", re.sub(r"^\[[^\]]*\]", "", t))


def search(name):
    """프로그램명 -> [(프로그램 URL, 제목)]. 드라마 섹션 검색."""
    # ponytail: 사이트 검색이 쉼표·붙여쓰기 차이에 약해서 첫 단어로만 검색하고 제목 비교는 _norm 으로
    term = re.sub(r"^\[[^\]]*\]\s*", "", name).split()[0]
    html = get(TV + "/tv/program-list-more", {"page": 1, "section": "DRAMA", "filter": "NAME", "term": term})
    return re.findall(r'<a href="(https://tv\.jtbc\.co\.kr/[^"]+)"[^>]*>.*?_dotdotdot">([^<]+)<', html, re.S)


def resolve(name):
    hits = search(name)
    exact = ([h for h in hits if _norm(h[1]) == _norm(name)]
             or [h for h in hits if _norm(h[1]).startswith(_norm(name))][:1])  # '시지프스 : the myth'
    if not exact:
        print(f"'{name}' 로 딱 맞는 프로그램을 못 찾음." + (" 후보:" if hits else ""))
        for url, title in hits[:10]:
            print(f"  {url}  {title}")
        return None
    url = exact[0][0]
    m = re.search(r"/replay/pr\d+/pm\d+", get(url))
    if not m:
        print("다시보기 메뉴 없음", name, url)
        return None
    print(f"찾음: {exact[0][1]} {url}")
    return TV + m.group()


def episodes(replay):
    """다시보기 목록 페이지를 돌며 [(회차 페이지 URL, 회차 라벨)]. 최신순."""
    seen, page = {}, 1
    while True:
        html = get(f"{replay}/paginate?page={page}")
        found = re.findall(r'href="(https://tv\.jtbc\.co\.kr/replay/[^"]+/ep\d+/view)".*?<strong>\s*([^<]*?)\s*</strong>', html, re.S)
        new = [(u, t) for u, t in found if u not in seen]
        if not new:
            return list(seen.items())
        seen.update(new)
        page += 1


def ep_num(label, last):
    """'[15회] 검사내전' -> '015', '[최종회]' -> 마지막 회차+1."""
    m = re.match(r"\[(\d+)회\]", label)
    if m:
        return m.group(1).zfill(3)
    if label.startswith("[최종회]"):
        return str(last + 1).zfill(3)
    return _safe(re.sub(r"[\[\]]", "", label))


def main(name, outdir):
    replay = resolve(name)
    if not replay:
        return
    eps = episodes(replay)
    last = max((int(m.group(1)) for _, t in eps if (m := re.match(r"\[(\d+)회\]", t))), default=0)
    title = _safe(name)
    base = Path(outdir) / title
    for url, label in reversed(eps):
        fname = f"{title}_{ep_num(label, last)}"
        vtt_path, srt_path = base / "vtt" / f"{fname}.vtt", base / "srt" / f"{fname}.srt"
        if vtt_path.exists() and srt_path.exists():
            continue
        try:
            pat = r"api\.jtbc\.co\.kr/v1/vod/(vo\d+)"
            cookie = None
            m = re.search(pat, get(url))
            if not m and _cookie():  # 19세 회차만 로그인 쿠키로 재시도 (만료된 쿠키는 다른 요청까지 막음)
                cookie = _cookie()
                m = re.search(pat, get(url, cookie=cookie))
            if not m:
                print("로그인 필요(19세)", fname, "- .env 의 JTBC_COOKIE 확인"); continue
            vo = m.group(1)
            tracks = json.loads(get(f"https://api.jtbc.co.kr/v1/vod/{vo}", cookie=cookie)).get("tracks") or []
            track = next((t for t in tracks if t.get("label") == "KR"), tracks[0] if tracks else None)
            if not track:
                print("자막없음", fname, label); continue
            raw = get(track["file"])
            for path in (vtt_path, srt_path):
                path.parent.mkdir(parents=True, exist_ok=True)
            vtt_path.write_text(raw, encoding="utf-8")
            srt_path.write_text(vtt_to_srt(raw), encoding="utf-8")
            print("저장", fname, vo)
        except Exception as e:
            print("실패", fname, label, e)


if __name__ == "__main__":
    args, outdir = sys.argv[1:], Path(__file__).resolve().parents[3] / "docs" / "JTBC"
    if args[:1] == ["-o"]:
        outdir, args = args[1], args[2:]
    for n in args:
        main(n, outdir)
