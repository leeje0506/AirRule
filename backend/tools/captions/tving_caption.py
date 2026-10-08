#!/usr/bin/env python3
"""TVING 프로그램별 한국어 자막(ko_cc_yn) 유무 확인.

사용: python3 tving_caption.py '<프로그램명>' ['<프로그램명>' ...]
      python3 tving_caption.py -f 목록.txt      (한 줄에 하나, 앞의 '- ' 는 무시)
      python3 tving_caption.py -a ...           (이름을 포함하는 프로그램 전부 — 배리어프리판·자막판 등)
출력: 프로그램별 자막 있는 회차 수 / 전체 회차 수 + 분류 요약
"""
import json, re, sys, urllib.parse, urllib.request

Q = ("screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900"
     "&apiKey=1e7952d0917d6aab1f0293a063697610")
SEARCH = "https://gw.tving.com/bff/search/v2/content/total/search?keyword={}&pageNo=1&pageSize=20&" + Q
EPS = ("https://api.tving.com/v2/media/frequency/program/{}?pageNo={}&pageSize=100&order=new"
       "&free=all&adult=all&scope=all&" + Q)
INFO = "https://api.tving.com/v2/media/content/info?mediaCode={}&" + Q
HDR = {"User-Agent": "Mozilla/5.0", "Origin": "https://www.tving.com", "Referer": "https://www.tving.com/"}


def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read())


def _norm(t):
    return re.sub(r"[\s:：]", "", t)


def search(name):
    """프로그램명 -> 제목이 정확히 같은 (code, title). 없으면 (None, 후보목록)."""
    data = get(SEARCH.format(urllib.parse.quote(name)))["data"]
    hits = [(i["code"], i["title"]) for b in data.get("bands") or []
            for i in b.get("items") or [] if str(i.get("code", "")).startswith("P")]
    exact = [h for h in hits if _norm(h[1]) == _norm(name)]
    return (exact[0], hits) if exact else (None, hits)


def episodes(pid):
    page = 1
    while True:
        body = get(EPS.format(pid, page))["body"]
        yield from body.get("result") or []
        if body.get("has_more") != "Y":
            return
        page += 1


def check(pid):
    """-> (자막 있는 회차 수, 전체 회차 수)."""
    eps = [e["episode"]["code"] for e in episodes(pid)]
    cc = sum(get(INFO.format(c))["body"]["content"].get("ko_cc_yn") == "Y" for c in eps)
    return cc, len(eps)


def expand(line):
    """'막돼먹은 영애씨 시즌1 ~ 17' -> 시즌1..시즌17."""
    m = re.fullmatch(r"(.*?시즌)\s*(\d+)\s*~\s*(\d+)", line)
    return [f"{m[1]}{i}" for i in range(int(m[2]), int(m[3]) + 1)] if m else [line]


def main(names, related=False):
    groups = {"전체 자막": [], "일부 자막": [], "자막 없음": [], "못 찾음": []}
    seen = set()
    for name in names:
        hit, cands = search(name)
        if related:  # 이름을 포함하는 모든 프로그램 (배리어프리판·자막판·일반판 등)
            targets = [h for h in cands if _norm(name).lower() in _norm(h[1]).lower()]
        else:
            targets = [hit] if hit else []
        if not targets:
            print(f"[못 찾음] {name}  후보: {', '.join(f'{t}({c})' for c, t in cands[:5]) or '-'}")
            groups["못 찾음"].append(name); continue
        for code, title in targets:
            if code in seen:
                continue
            seen.add(code)
            cc, total = check(code)
            key = "자막 없음" if cc == 0 else "전체 자막" if cc == total else "일부 자막"
            print(f"[{key}] {title} ({code}) {cc}/{total}")
            groups[key].append(f"{title} ({cc}/{total})")
    print("\n=== 요약 ===")
    for k, v in groups.items():
        print(f"{k} {len(v)}: {', '.join(v) or '-'}")


if __name__ == "__main__":
    args = sys.argv[1:]
    related = args[:1] == ["-a"]
    if related:
        args = args[1:]
    if args[:1] == ["-f"]:
        lines = open(args[1], encoding="utf-8").read().splitlines()
        args = [l.strip().lstrip("-").strip() for l in lines if l.strip()]
    main([n for a in args for n in expand(a)], related)
