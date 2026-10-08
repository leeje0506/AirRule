"""
프로그램 찾기 — 방송사 다시보기에서 프로그램 검색 → 회차별 자막 유무 → 자막 받기.
지원: KBS·MBC·SBS·JTBC·TV조선·채널A·MBN·TVING (자막 받기 — TVING 최근 작품은 유무만), 웨이브·쿠팡플레이 (유무만).

CLI 판: backend/tools/captions/ (대량 수집·통합본 분할).
버셀 무료 플랜 아끼기:
  - 자막 파일은 사이트 CDN 이 CORS 를 열어 둬서(MBC·JTBC) 회차 목록에 주소만 실어 주고 브라우저가 직접 받는다.
    VTT→SRT 변환·zip 도 브라우저(frontend/src/utils/vtt.js). 서버 경유(/files, 10화 묶음)는
    CORS 가 막힌 사이트(MBN)나 직접 받기 실패 때만.
  - 통합 검색은 서버 한 번 호출 안에서 사이트별 동시 검색.
  - 검색·회차 목록은 인스턴스 메모리 + 브라우저에 10분 캐시.
TVING 은 공개 회차 정보(vtt_path)로 공개 자막 파일 주소를 만든다 — 로그인 불필요. 최근 작품(cloudfront)은 유무만.
"""
import json
import os
import re
import urllib.parse
import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth import get_current_user

router = APIRouter(prefix="/api/captions", tags=["captions"])
UA = "Mozilla/5.0"


def _get(url, headers=None, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, body, {"User-Agent": UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8-sig", "replace")


def _norm(t):
    """공백·문장부호·[무삭제판] 같은 머리말 무시하고 비교."""
    return re.sub(r"[\W_]+", "", re.sub(r"^\[[^\]]*\]", "", t or "")).lower()


def _rank(q, hits):
    """[(id, title)] → 제목 일치도순 [{id, title, exact}]."""
    w = _norm(q)
    hits = sorted(dict(hits).items(), key=lambda h: (_norm(h[1]) != w, not _norm(h[1]).startswith(w),
                                                      w not in _norm(h[1]), len(h[1])))
    return [{"id": i, "title": t, "exact": _norm(t) == w} for i, t in hits]


def _num(label):
    m = re.search(r"\d+", label or "")
    return int(m.group()) if m else None


def _pmap(fn, items):
    # ponytail: 고정 8스레드 — 회차가 수백 개면 함수 시간 한도(버셀) 근처까지 갈 수 있음
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(fn, items))


# 가드: 회차마다 자막을 확인하는 사이트(JTBC·MBN·TVING·웨이브)는 최근 N화만 확인한다.
# 700화짜리 MBN 프로그램 하나가 CPU 6.5초·20초 걸려 버셀 시간 한도에 닿을 수 있어서. 오래된 회차는 목록만.
CHECK_LIMIT = 200
SKIP = "skip"
SKIP_NOTE = f"회차가 많아 최근 {CHECK_LIMIT}화만 확인"


def _check_recent(fn, items):
    """items 는 최신순. 앞 CHECK_LIMIT 개만 fn 으로 확인하고 나머지는 SKIP."""
    return _pmap(fn, items[:CHECK_LIMIT]) + [SKIP] * max(0, len(items) - CHECK_LIMIT)


# 가드: 회차 목록은 최근 LIST_LIMIT 화까지만 (인간극장 같은 수천 회 프로그램이 쪽을 순서대로 받다 시간 초과).
# 첫 쪽에서 전체 쪽수를 읽고 나머지는 동시에, 실패한 쪽은 한 번 더 시도.
LIST_LIMIT = 1000


def _pages(fetch, first, total_pages, per_page):
    """first = 1쪽 결과. 2쪽부터 최근 LIST_LIMIT 화가 되는 쪽까지 동시에 받아 [1쪽, 2쪽, …]. 반환 (쪽들, 잘렸는지)."""
    want = min(int(total_pages or 1), -(-LIST_LIMIT // per_page))

    def safe(n):
        for _ in range(2):
            try:
                return fetch(n)
            except Exception:
                pass
        return None
    rest = _pmap(safe, range(2, want + 1))
    return [first] + [r for r in rest if r is not None], want < int(total_pages or 1)


_CACHE = {}
TTL = 600


def _cached(key, fn, ttl=TTL):
    """같은 인스턴스(fluid compute 재사용) 안에서 캐시. ponytail: 프로세스 메모리 — 인스턴스마다 따로."""
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    if len(_CACHE) > 200:
        _CACHE.clear()
    _CACHE[key] = (time.time(), val)
    return val


def _ext(text, url=""):
    """자막 원본 형식 — 내용 머리로 판별, 애매하면 주소 확장자."""
    head = text.lstrip("\ufeff")[:200]
    if head.startswith("WEBVTT"):
        return "vtt"
    if re.match(r"\d+\r?\n\d{2}:\d{2}:\d{2},\d{3} -->", head):
        return "srt"
    return (urllib.parse.urlparse(url).path.rsplit(".", 1)[-1] or "txt").lower()


# ── MBC ──────────────────────────────────────────────────────────

MBC_HDR = {"Referer": "https://playvod.imbc.com/"}


def mbc_search(q):
    if q.isdigit():
        return [{"id": q, "title": q, "exact": True}]
    data = json.loads(_get(f"https://cue.imbc.com/api/program.aspx?query={urllib.parse.quote(q)}&startNum=0", MBC_HDR))
    return _rank(q, [(p["ProgramCode"], re.sub(r"<[^>]+>", "", p["ProgramTitle"]))
                     for p in data.get("nProgramList") or []])


def mbc_episodes(pid):
    eps, page = [], 1
    while True:
        data = json.loads(_get("https://playvod.imbc.com/api/ContentList_Templete?programId="
                               f"{pid}&orderBy=d&selectYear=0&curPage={page}&pageSize=100", MBC_HDR))
        for e in data["ContList"]:
            label = (e["ContentNumber"] or e["BroadDate"] or "").strip()
            cap = e["CaptionYN"] == "Y"
            eps.append({"key": f"{pid}/{e['ContentId']}", "label": label, "num": _num(label), "caption": cap,
                        "format": "vtt" if cap else None,
                        "url": f"https://playvod.imbc.com/caption/{pid}/caption_{e['ContentId']}.vtt" if cap else None})
        if page * 100 >= data["TotalCount"]:
            return eps
        page += 1


def mbc_raw(key):
    if not re.fullmatch(r"\d+/\d+", key):
        raise HTTPException(400, "잘못된 회차 키")
    pid, cid = key.split("/")
    url = f"https://playvod.imbc.com/caption/{pid}/caption_{cid}.vtt"
    text = _get(url, MBC_HDR)
    return text, _ext(text, url)


# ── JTBC ─────────────────────────────────────────────────────────

JTBC = "https://tv.jtbc.co.kr"
JTBC_HDR = {"Origin": JTBC, "Referer": JTBC + "/"}


def _jtbc(url, cookie=False):
    c = os.environ.get("JTBC_COOKIE") if cookie else None   # 19세 회차용 로그인 쿠키
    return _get(url, {**JTBC_HDR, **({"Cookie": c} if c else {})})


def jtbc_search(q):
    # ponytail: 사이트 검색이 붙여쓰기 차이에 약해서 첫 단어로 검색하고 비교는 _norm 으로 (드라마 섹션만)
    term = re.sub(r"^\[[^\]]*\]\s*", "", q).split()[0]
    html = _get(JTBC + "/tv/program-list-more", JTBC_HDR,
                {"page": 1, "section": "DRAMA", "filter": "NAME", "term": term})
    return _rank(q, re.findall(r'<a href="(https://tv\.jtbc\.co\.kr/[^"]+)"[^>]*>.*?_dotdotdot">([^<]+)<', html, re.S))


def _jtbc_vo(url):
    """회차 페이지 → vo id (없으면 쿠키로 재시도) → 자막 트랙.
    반환: (vo, 확장자, 파일주소) 자막 있음 / False 자막 없음 / "login" 19세라 로그인 필요(확인 불가) / None 오류."""
    pat = r"api\.jtbc\.co\.kr/v1/vod/(vo\d+)"
    try:
        m = re.search(pat, _jtbc(url)) or (os.environ.get("JTBC_COOKIE") and re.search(pat, _jtbc(url, True)))
        if not m:
            return "login"   # 19세 회차는 로그인 페이지로 넘어가 vo 가 안 보인다
        tracks = json.loads(_jtbc(f"https://api.jtbc.co.kr/v1/vod/{m.group(1)}", True)).get("tracks") or []
        track = next((t for t in tracks if t.get("label") == "KR"), tracks[0] if tracks else None)
        return (m.group(1), _ext("", track["file"]), track["file"]) if track else False
    except Exception:
        return None


def jtbc_episodes(url):
    if not url.startswith(JTBC + "/"):
        raise HTTPException(400, "JTBC 프로그램 주소가 아닙니다")
    m = re.search(r"/replay/pr\d+/pm\d+", _get(url, JTBC_HDR))
    if not m:
        return []
    replay, seen, page = JTBC + m.group(), {}, 1
    while True:
        html = _get(f"{replay}/paginate?page={page}", JTBC_HDR)
        new = [(u, t) for u, t in re.findall(
            r'href="(https://tv\.jtbc\.co\.kr/replay/[^"]+/ep\d+/view)".*?<strong>\s*([^<]*?)\s*</strong>', html, re.S)
            if u not in seen]
        if not new:
            break
        seen.update(new)
        page += 1
    items = list(seen.items())
    vos = _check_recent(lambda it: _jtbc_vo(it[0]), items)   # 다시보기 목록은 최신순
    out = []
    for (_, label), vo in zip(items, vos):
        got = isinstance(vo, tuple)
        out.append({"key": vo[0] if got else "", "label": label, "num": _num(label),
                    "caption": True if got else (False if vo is False else None),   # None = 확인 불가
                    "format": vo[1] if got else None, "url": vo[2] if got else None,
                    **({"note": "19세 — 로그인 필요"} if vo == "login" else {"note": SKIP_NOTE} if vo == SKIP else {})})
    return out


def jtbc_raw(vo):
    if not re.fullmatch(r"vo\d+", vo):
        raise HTTPException(400, "잘못된 회차 키")
    tracks = json.loads(_jtbc(f"https://api.jtbc.co.kr/v1/vod/{vo}", True)).get("tracks") or []
    track = next((t for t in tracks if t.get("label") == "KR"), tracks[0] if tracks else None)
    if not track:
        raise HTTPException(404, "자막 없음")
    text = _jtbc(track["file"])
    return text, _ext(text, track["file"])


# ── TVING ───────────────────────────────────────────

TQ = ("screenCode=CSSD0100&networkCode=CSND0900&osCode=CSOD0900&teleCode=CSCD0900"
      "&apiKey=1e7952d0917d6aab1f0293a063697610")
TVING_HDR = {"Origin": "https://www.tving.com", "Referer": "https://www.tving.com/"}


def tving_search(q):
    data = json.loads(_get("https://gw.tving.com/bff/search/v2/content/total/search?keyword="
                           f"{urllib.parse.quote(q)}&pageNo=1&pageSize=20&{TQ}", TVING_HDR))["data"]
    return _rank(q, [(i["code"], i["title"]) for b in data.get("bands") or []
                     for i in b.get("items") or [] if str(i.get("code", "")).startswith("P")])


def tving_episodes(pid):
    if not re.fullmatch(r"P\d+", pid):
        raise HTTPException(400, "잘못된 프로그램 코드")
    eps, page = [], 1
    while True:
        body = json.loads(_get(f"https://api.tving.com/v2/media/frequency/program/{pid}?pageNo={page}"
                               f"&pageSize=100&order=new&free=all&adult=all&scope=all&{TQ}", TVING_HDR))["body"]
        eps += body.get("result") or []
        if body.get("has_more") != "Y":
            break
        page += 1

    def cc(e):
        """회차 정보 → (자막 유무, 자막 주소). 자막 VTT 는 썸네일 위치표(vtt_path)와 같은 폴더에 공개돼 있다:
        …/vtt/{이름}_vtt.vtt → …/{이름}_KO_CC.vtt. 최근 작품은 썸네일이 cloudfront 라 규칙을 못 씀(주소 None)."""
        try:
            d = json.loads(_get(f"https://api.tving.com/v2/media/episode/{e['episode']['code']}?{TQ}", TVING_HDR))
            ep = d["body"]["episode"]
            if ep.get("ko_cc_yn") != "Y":
                return False, None
            m = re.fullmatch(r"https?://image-pip\.tving\.com/(.+)/vtt/(\w+)_vtt\.vtt", ep.get("vtt_path") or "")
            return True, f"https://image-pip.tving.com/{m.group(1)}/{m.group(2)}_KO_CC.vtt" if m else None
        except Exception:
            return None, None
    flags = [(None, SKIP) if x == SKIP else x for x in _check_recent(cc, eps)]   # order=new → 최신순
    return [{"key": "" if url == SKIP else url or "", "label": f"{e['episode']['frequency']}회", "num": e["episode"]["frequency"],
             "caption": f, "format": "vtt" if url and url != SKIP else None, "url": None if url == SKIP else url,
             **({"note": SKIP_NOTE} if url == SKIP else {} if url or not f else {"note": "주소 확인 불가"})}
            for e, (f, url) in zip(eps, flags)]


TVING_CC = re.compile(r"https://image-pip\.tving\.com/[\w/]+_KO_CC\.vtt")


def tving_raw(url):
    if not TVING_CC.fullmatch(url):
        raise HTTPException(400, "잘못된 회차 키")
    text = _get(url)
    return text, _ext(text, url)


# ── KBS ─────────────────────────────────────────────────────────

KBS_CAP = "https://mediafactory.play.kbs.co.kr/upload/caption/"


def kbs_search(q):
    d = json.loads(_get("https://reco.kbs.co.kr/v2/search/program?" + urllib.parse.urlencode(
        dict(target="program_web", keyword=q, page=1, page_size=20, sort_option="date"))))
    return _rank(q, [(p["program_code"], p["program_title"]) for p in d.get("data") or []])


def kbs_episodes(pc):
    if not re.fullmatch(r"[\w-]+", pc):
        raise HTTPException(400, "잘못된 프로그램 코드")
    def fetch(n):   # page_size 최대 40, 최신순
        return json.loads(_get("https://static.api.kbs.co.kr/mediafactory/v1/contents?" + urllib.parse.urlencode(
            dict(program_code=pc, sort_option="program_planned_date|desc", page=n, page_size=40))))
    first = fetch(1)
    pages, limited = _pages(fetch, first, first.get("page_count"), 40)
    eps = []
    for d in pages:
        for e in d.get("data") or []:
            if e.get("descriptive_video_service_yn") == "Y":   # 화면해설판은 빼기
                continue
            url = next((c["url"] for c in e.get("custom_caption") or [] if c.get("language") == "ko"), None)
            no = e.get("program_sequence_number")
            eps.append({"key": url or "", "label": f"{no}회" if no else e.get("program_id", ""), "num": _num(str(no or "")),
                        "caption": bool(url), "format": _ext("", url) if url else None, "url": url})
    return eps, limited


def kbs_raw(url):
    if not url.startswith(KBS_CAP) or ".." in url:
        raise HTTPException(400, "잘못된 회차 키")
    text = _get(url)
    return text, _ext(text, url)


# ── SBS ─────────────────────────────────────────────────────────

def sbs_search(q):
    d = json.loads(_get("https://apis.sbs.co.kr/allvod-api/search/list?q=" + urllib.parse.quote(q)))
    return _rank(q, [(i["id"], i["title"]) for i in (d.get("search_content") or {}).get("items") or []])


def _sbs_url(pid, mid):
    return f"https://static.cloud.sbs.co.kr/vod-sub-title/{pid}/{mid}.vtt"


def sbs_episodes(pid):
    if not re.fullmatch(r"\w+", pid):
        raise HTTPException(400, "잘못된 프로그램 코드")
    def fetch(n):   # 쪽당 최대 300, 최신순
        return json.loads(_get(f"https://static.apis.sbs.co.kr/allvod-api/media_sub/vod/{pid}?" + urllib.parse.urlencode(
            {"jwt-token": "", "page": n, "sort": "new", "free_yn": "", "srs_id": "", "srs_year": ""})))["media"]
    mid = lambda e: e["mda_id"]["items"][0]["id"]   # noqa: E731
    first = fetch(1)
    got = first.get("items") or []
    tot = int(first.get("tot_cnt") or 0)
    items = {mid(e): e for e in got}
    if len(got) < tot:
        # SBS 는 쪽마다 300개를 주지만 다음 쪽은 몇 개(런닝맨 28)만 밀린다 — 1·2쪽을 비교해 밀리는 폭을 구하고
        # 최근 LIST_LIMIT 개를 덮는 쪽까지만 동시에 받아 중복 제거.
        second = fetch(2).get("items") or []
        ids = [mid(e) for e in got]
        step = ids.index(mid(second[0])) if second and mid(second[0]) in ids else len(got)
        step = step or len(got)
        need = 2 + -(-max(0, min(tot, LIST_LIMIT) - len(got) - step) // step)
        for e in second + [e for m in _pmap(lambda n: fetch(n).get("items") or [], range(3, need + 1)) for e in m]:
            items.setdefault(mid(e), e)
    limited = tot > LIST_LIMIT
    items = list(items.values())
    out = []
    for e in items:
        mid = e["mda_id"]["items"][0]["id"]
        no = (e.get("episode") or {}).get("number")
        cap = e.get("vod_ctt_yn") == "Y"
        out.append({"key": f"{pid}/{mid}", "label": f"{no}회" if no else e.get("brd_beg_dd", ""), "num": _num(str(no or "")),
                    "caption": cap, "format": "vtt" if cap else None, "url": _sbs_url(pid, mid) if cap else None})
    return out, limited


def sbs_raw(key):
    if not re.fullmatch(r"\w+/\d+", key):
        raise HTTPException(400, "잘못된 회차 키")
    url = _sbs_url(*key.split("/"))
    text = _get(url)
    return text, _ext(text, url)


# ── TV조선 ───────────────────────────────────────────────────────

def tvc_search(q):
    rows = json.loads(_get("https://broadcast.tvchosun.com/index/getListMore.cstv", data=dict(
        type="sort", startNum=0, endNum=30, program_div=0, search_text=q)))
    return _rank(q, [(r["prog_id"], r["prog_name"]) for r in rows])


def tvc_episodes(pid):
    if not re.fullmatch(r"C\d+", pid):
        raise HTTPException(400, "잘못된 프로그램 코드")
    def fetch(n):   # 쪽당 10, 최신순
        return json.loads(_get("https://vod.tvchosun.com/vod/getVodReplayOrderByPagingInfo.cstv", data=dict(
            prog_id=pid, order_type="latest", page=n, search_text="", year="all")))[0]
    first = fetch(1)
    pages, limited = _pages(fetch, first, first["replayTotalPages"], 10)
    eps = []
    for r in pages:
        for e in r["prog"]:
            cap, no = e["vtt_yn"] == "Y", e["epis_sub_cnt"]
            eps.append({"key": f"{pid}/{no}", "label": f"{no}회", "num": _num(str(no)), "caption": cap,
                        "format": "vtt" if cap else None,
                        "url": f"https://img.tvchosun.com/upload_img/vtt/{pid}/{pid}_{no}.vtt" if cap else None})
    return eps, limited


def tvc_raw(key):
    if not re.fullmatch(r"C\d+/\d+", key):
        raise HTTPException(400, "잘못된 회차 키")
    pid, no = key.split("/")
    url = f"https://img.tvchosun.com/upload_img/vtt/{pid}/{pid}_{no}.vtt"
    text = _get(url)
    return text, _ext(text, url)


# ── 채널A ───────────────────────────────────────────────────────

def cha_search(q):
    progs = _cached(("cha-programs",), lambda: json.loads(_get(
        "https://ichannela.com/program/main/program_by_genre.do",
        data=dict(catecode="all", search="all", sort="all")))["programList"], ttl=86400)
    w = _norm(q)
    return _rank(q, [(f"{p['CATE_CODE']}/{p['WPGM_ID']}", p["CATE_NAME"].strip()) for p in progs
                     if w in _norm(p["CATE_NAME"])])


def cha_episodes(pid):
    if not re.fullmatch(r"[\w]+/[\w]+", pid):
        raise HTTPException(400, "잘못된 프로그램 코드")
    cate, wpgm = pid.split("/")
    rows = json.loads(_get("https://ichannela.com/program/detail/program_replaylist.do?" + urllib.parse.urlencode(
        dict(prg_code=cate, pgm_id=wpgm, nowPage=1, perPageCnt=2000, sort="N", video_attr=20))))["pgm_replayList"]
    return [{"key": e["CC_FILE_PATH"] or "", "label": f"{e['EPISODE_NO']}회" if e["EPISODE_NO"] else e["TITLE"].strip(),
             "num": _num(str(e["EPISODE_NO"])), "caption": bool(e["CC_FILE_PATH"]),
             "format": _ext("", e["CC_FILE_PATH"]) if e["CC_FILE_PATH"] else None,
             "url": "https://image.ichannela.com" + e["CC_FILE_PATH"] if e["CC_FILE_PATH"] else None} for e in rows]


def cha_raw(path):
    if not re.fullmatch(r"/images/program/[\w/.-]+\.\w+", path) or ".." in path:
        raise HTTPException(400, "잘못된 회차 키")
    url = "https://image.ichannela.com" + path
    text = _get(url)
    return text, _ext(text, url)


# ── MBN ─────────────────────────────────────────────────────────

MBN = "https://www.mbn.co.kr"


def _mbn_programs():
    """방영 중(VOD 메뉴) + 종영(finishProgram 페이지들) 프로그램 목록. 하루 캐시."""
    def page(url):
        try:
            h = _get(url)
        except Exception:
            return []
        return (re.findall(r"programMain\.php\?progCode=(\d+)'>\s*([^<]+?)\s*</a>", h)
                + re.findall(r'programMain/(\d+)"[^>]*>\s*<img[^>]*alt="([^"]+)"', h))
    urls = [f"{MBN}/vod/enter", f"{MBN}/vod/drama", f"{MBN}/vod/culture"] + [f"{MBN}/vod/finishProgram/p{i}" for i in range(1, 21)]
    return dict(pair for rows in _pmap(page, urls) for pair in rows)


def mbn_search(q):
    progs = _cached(("mbn-programs",), _mbn_programs, ttl=86400)
    w = _norm(q)
    return _rank(q, [(code, name) for code, name in progs.items() if w in _norm(name)])


def _mbn_info(seq):
    return json.loads(_get(f"{MBN}/player/mbnVodPlayer_2020.mbn?content_cls_cd=20&content_id={seq}&relay_type=1"))


def mbn_episodes(prog):
    if not prog.isdigit():
        raise HTTPException(400, "잘못된 프로그램 코드")
    m = re.search(rf"programContents/{prog}/(\d+)", _get(f"{MBN}/vod/programMain/{prog}"))
    if not m:
        return []
    def page(n):
        return _get(f"{MBN}/lib/module/program/getProgramReviewList_E.v2.php", data=dict(
            menuType=50, menuCode=m.group(1), progCode=prog, page=n, searchKey="", searchWord=""))
    first = page(1)   # 전체 쪽수는 goPage('N') 로 나온다 — 나머지 쪽은 동시에
    last = max([int(n) for n in re.findall(r"goPage\('(\d+)'\)", first)] or [1])
    items = {}
    for h in [first] + _pmap(page, range(2, last + 1)):
        items.update((seq, t) for seq, t in re.findall(rf'previewlist/{prog}/\d+/(\d+)">\s*([^<]+?)\s*</a>', h)
                     if seq not in items)

    def sub(seq):
        try:
            return _mbn_info(seq).get("subtitle_path") or None
        except Exception:
            return None
    subs = _check_recent(sub, list(items))   # 다시보기 목록 1쪽이 최신
    return [{"key": seq, "label": t, "num": _num(t), "caption": None, "format": None, "url": None, "note": SKIP_NOTE}
            if u == SKIP else
            {"key": seq, "label": t, "num": _num(t), "caption": bool(u), "format": _ext("", u) if u else None, "url": u}
            for (seq, t), u in zip(items.items(), subs)]


def mbn_raw(seq):
    if not seq.isdigit():
        raise HTTPException(400, "잘못된 회차 키")
    url = _mbn_info(seq).get("subtitle_path")
    if not url:
        raise HTTPException(404, "자막 없음")
    text = _get(url)
    return text, _ext(text, url)


# ── 웨이브 (유무만) ───────────────────────────────────────────────

WQ = dict(apikey="E5F3E0D30947AA5440556471321BB6D9", credential="none", device="pc", drm="wm",
          partner="pooq", pooqzone="none", region="kor", targetage="all")   # wavve.com 웹 공개 키


def _wavve(path, **p):
    return json.loads(_get("https://apis.wavve.com" + path + "?" + urllib.parse.urlencode({**p, **WQ})))


def wavve_search(q):
    cells = _wavve("/fz/search/list.js", keyword=q, type="program", orderby="score", limit=20, offset=0,
                   data="catalog")["cell_toplist"]["celllist"]
    hits = []
    for c in cells:
        url = next((e["url"] for e in c.get("event_list") or [] if "programid=" in e.get("url", "")), None)
        if url:
            hits.append((url.split("programid=")[1].split("&")[0], c.get("alt") or ""))
    return _rank(q, hits)


def wavve_episodes(pid):
    if not re.fullmatch(r"[\w.]+", pid):
        raise HTTPException(400, "잘못된 프로그램 코드")
    eps, off = [], 0
    while True:
        page = _wavve(f"/fz/vod/programs/{pid}/contents", orderby="new", limit=50, offset=off)["cell_toplist"]["celllist"]
        if not page:
            break
        eps += page
        off += len(page)

    def cc(e):
        try:
            d = _wavve("/fz/vod/contents-detail/" + e["contentid"])
            return d.get("isCC") == "y" or any(x.get("subtitleLang", "").startswith("ko") for x in d.get("subtitles") or [])
        except Exception:
            return None
    flags = _check_recent(cc, eps)
    return [{"key": "", "label": f"{e.get('episodenumber')}회" if e.get("episodenumber") else e.get("episodetitle", ""),
             "num": _num(str(e.get("episodenumber") or "")), "caption": None if f == SKIP else f, "format": None, "url": None,
             **({"note": SKIP_NOTE} if f == SKIP else {})}
            for e, f in zip(eps, flags)]


# ── 쿠팡플레이 (유무만) ───────────────────────────────────────────
# ponytail: Akamai 봇 차단 — 연속 호출이 많으면 403. 시즌당 1번만 부르고, 막히면 그 사이트만 실패로 보인다.

CP_HDR = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36",
          "x-platform": "WEBCLIENT", "Referer": "https://www.coupangplay.com/"}


def _cp(path, **q):
    return json.loads(_get("https://www.coupangplay.com/api-discover" + path + "?" + urllib.parse.urlencode(
        {"platform": "WEBCLIENT", "locale": "ko", **q}), CP_HDR))


def coupang_search(q):
    items = _cp("/v3/search", query=q, page=1, perPage=20)["data"]["contents"]
    return _rank(q, [(c["id"], c.get("title") or "") for c in items if c.get("type") == "TITLE"])


def coupang_episodes(tid):
    if not re.fullmatch(r"[0-9a-f-]{36}", tid):
        raise HTTPException(400, "잘못된 프로그램 코드")
    t = _cp(f"/v1/discover/titles/{tid}", filterRestrictedContent="false")["data"]
    ko = lambda langs: "한국어" in (langs or [])   # noqa: E731  — 'languages' = 자막 언어 목록
    seasons = t.get("seasonList") or []
    if not seasons:   # 영화 등 단편
        return [{"key": "", "label": t.get("title") or "본편", "num": None, "caption": ko(t.get("languages")),
                 "format": None, "url": None}]
    eps = []
    for season in seasons:
        for e in _cp(f"/v2/discover/titles/{tid}/episodes", sort="true", page=1, perPage=100, season=season).get("data") or []:
            label = (f"시즌{e.get('season')} " if len(seasons) > 1 else "") + f"{e.get('episode')}회"
            eps.append({"key": "", "label": label, "num": e.get("episode"), "caption": ko(e.get("languages")),
                        "format": None, "url": None})
    return eps


# direct = 자막 CDN 이 CORS 를 열어 둬서 브라우저가 바로 받을 수 있음 (버셀 함수 안 씀)
SOURCES = {
    "mbc": dict(search=mbc_search, episodes=mbc_episodes, raw=mbc_raw, direct=True),
    "jtbc": dict(search=jtbc_search, episodes=jtbc_episodes, raw=jtbc_raw, direct=True),
    "kbs": dict(search=kbs_search, episodes=kbs_episodes, raw=kbs_raw, direct=True),
    "sbs": dict(search=sbs_search, episodes=sbs_episodes, raw=sbs_raw, direct=True),
    "tvchosun": dict(search=tvc_search, episodes=tvc_episodes, raw=tvc_raw, direct=True),
    "channela": dict(search=cha_search, episodes=cha_episodes, raw=cha_raw, direct=True),
    "mbn": dict(search=mbn_search, episodes=mbn_episodes, raw=mbn_raw, direct=False),   # CORS 가 mbn.co.kr 전용
    "tving": dict(search=tving_search, episodes=tving_episodes, raw=tving_raw, direct=True),   # 회차 정보가 image-pip 인 작품만 받기 가능, 나머지는 유무만
    "wavve": dict(search=wavve_search, episodes=wavve_episodes, raw=None, direct=False),  # 유무만
    "coupang": dict(search=coupang_search, episodes=coupang_episodes, raw=None, direct=False),  # 유무만
}


def _source(name):
    if name not in SOURCES:
        raise HTTPException(400, "지원하지 않는 출처")
    return SOURCES[name]


def _call(fn, *args):
    try:
        return fn(*args)
    except HTTPException:
        raise
    except Exception as e:  # 외부 사이트 오류는 화면에 사유로 보여준다
        raise HTTPException(502, f"{type(e).__name__}: {e}")


def _site_search(source, q):
    """사이트 검색 + 띄어쓰기 보정 — '밤을걷는선비' 처럼 붙여 쓰면 못 찾는 사이트(JTBC·TV조선)가 있어서,
    딱 맞는 게 없고 검색어에 공백이 없으면 앞 두 글자로 다시 찾아 공백 무시하고 검색어를 포함한 것만 더한다."""
    fn = SOURCES[source]["search"]
    res = _cached(("s", source, q), lambda: fn(q))
    w = _norm(q)
    if any(r["exact"] for r in res) or " " in q.strip() or len(w) < 3:
        return res
    seen = {r["id"] for r in res}
    more = [{**r, "exact": _norm(r["title"]) == w} for r in _cached(("s", source, q[:2]), lambda: fn(q[:2]))
            if r["id"] not in seen and w in _norm(r["title"])]
    return sorted(more + res, key=lambda r: not r["exact"])


def _search_one(source, q):
    try:
        return [{**r, "source": source} for r in _site_search(source, q)[:20]], None
    except Exception as e:
        return [], {"source": source, "detail": f"{type(e).__name__}: {e}"}


@router.get("/search")
def search(source: str, q: str, response: Response, _=Depends(get_current_user)):
    """source=all 이면 모든 사이트를 서버 한 번 호출 안에서 동시에 — 실패한 사이트는 errors 로."""
    q = q.strip()
    if not q:
        raise HTTPException(400, "프로그램명을 입력하세요")
    if source != "all":
        _source(source)   # 잘못된 출처면 400
    sites = list(SOURCES) if source == "all" else [source]
    out = _pmap(lambda s: _search_one(s, q), sites)
    response.headers["Cache-Control"] = f"private, max-age={TTL}"
    return {"results": [r for rs, _ in out for r in rs], "errors": [e for _, e in out if e]}


@router.get("/episodes")
def episodes(source: str, id: str, response: Response, _=Depends(get_current_user)):
    src = _source(source)
    got = _cached(("e", source, id), lambda: _call(src["episodes"], id))
    eps, limited = got if isinstance(got, tuple) else (got, False)   # (회차, 최근 LIST_LIMIT 화로 잘렸는지)
    eps.sort(key=lambda e: (e["num"] is None, e["num"] or 0, e["label"]))
    response.headers["Cache-Control"] = f"private, max-age={TTL}"
    return {"episodes": eps, "downloadable": src["raw"] is not None, "direct": src["direct"],
            "limited": LIST_LIMIT if limited else None}


class FilesRequest(BaseModel):
    source: str
    keys: list[str]


@router.post("/files")
def caption_files(body: FilesRequest, _=Depends(get_current_user)):
    """서버 경유 받기 — 직접 받기가 안 되는 사이트(MBN)나 직접 받기가 실패했을 때만.
    호출 수를 아끼려고 최대 10화씩 묶어서 받는다. 원본 그대로 주고 SRT 변환은 브라우저가 한다."""
    raw = _source(body.source)["raw"]
    if raw is None:
        raise HTTPException(400, "이 사이트는 자막 유무만 확인할 수 있습니다 (추출 불가)")
    if not 0 < len(body.keys) <= 10:
        raise HTTPException(400, "한 번에 1~10화")

    def one(key):
        try:
            text, ext = raw(key)
            return {"key": key, "text": text, "ext": ext}
        except HTTPException as e:
            return {"key": key, "error": e.detail}
        except Exception as e:
            return {"key": key, "error": f"{type(e).__name__}: {e}"}
    return {"files": _pmap(one, body.keys)}


# ── 주소로 받기 예비 경로 ───────────────────────────────────────────
# 브라우저 직접 받기를 막은 자막 서버(TVING 최근 작품·MBN 등)만 서버가 대신 받는다.
# 아무 주소나 대리 요청하면 남용될 수 있어서 지원 사이트의 자막 호스트·자막 확장자만 허용.
CAPTION_HOSTS = {
    "tving-vod-cloudfront.tving.com", "image-pip.tving.com", "img.mbn.co.kr", "playvod.imbc.com",
    "fs.jtbc.co.kr", "mediafactory.play.kbs.co.kr", "static.cloud.sbs.co.kr", "img.tvchosun.com",
    "image.ichannela.com",
}
CAPTION_EXT = (".vtt", ".srt", ".smi", ".ttml", ".xml")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):   # 허용 호스트가 다른 곳으로 넘기는 것도 따라가지 않는다
        return None


_no_redirect = urllib.request.build_opener(_NoRedirect)


class UrlsRequest(BaseModel):
    urls: list[str]


@router.post("/fetch")
def fetch_urls(body: UrlsRequest, _=Depends(get_current_user)):
    if not 0 < len(body.urls) <= 10:
        raise HTTPException(400, "한 번에 1~10개")

    def one(url):
        u = urllib.parse.urlparse(url)
        if u.scheme != "https" or u.hostname not in CAPTION_HOSTS or not u.path.lower().endswith(CAPTION_EXT):
            return {"url": url, "error": "지원 사이트의 자막 파일 주소만 서버로 받을 수 있습니다"}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            raw = _no_redirect.open(req, timeout=20).read(5_000_001)   # 자막은 수백 KB — 5MB 넘으면 거절
            if len(raw) > 5_000_000:
                return {"url": url, "error": "파일이 너무 큽니다"}
            text = raw.decode("utf-8-sig", "replace")
            return {"url": url, "text": text, "ext": _ext(text, url)}
        except Exception as e:
            return {"url": url, "error": f"{type(e).__name__}: {e}"}
    return {"files": _pmap(one, body.urls)}
