"""초기 데이터 시드 스크립트 (정책 매트릭스 구조)."""
from sqlalchemy.orm import Session
from app.models import (
    User, Broadcaster,
    PolicyCategory, PolicyItem, PolicyValue, PolicyValueHistory,
    TechItem, Mapping, ItemTechLink,
    gen_id, utcnow,
)
from app.auth import hash_password

try:
    from app.seed_source_codes import SOURCE_CODES
except ImportError:
    SOURCE_CODES = {}


# 방송사 코드 → id
BC = {"JTBC": "b_jtbc", "LGHV": "b_lghv", "SKBB": "b_skbb",
      "TVCS": "b_tvcs", "DLIV": "b_dliv", "TVING": "b_tvng"}


# ── 엑셀 시트 → 정책 매트릭스 ──────────────────────────────────────
#   구조: (카테고리, [ (항목명, 설명, { 방송사: (summary, detail) }) ])
#   summary = 전체 탭용 짧은 값 (O / X / △ / 18글자 …)
#   detail  = 방송사별 탭용 풀어쓴 전문 (없으면 빈 문자열)
POLICY_MATRIX = [
    ("싱크", [
        ("일반", "영상 내 음성에 맞게 싱크 생성/조정 작업", {
            "DLIV": ("O", "싱크 시작 지점을 정확하게 보정 (자막 시작이 음성보다 빠르지 않도록)"),
            "LGHV": ("O", ""), "SKBB": ("O", ""), "JTBC": ("O", ""),
            "TVCS": ("O", ""), "TVING": ("O", ""),
        }),
        ("오버랩", "영상 내 음성이 겹치는 경우 오버랩 작업", {
            "DLIV": ("O", "오버랩 구간일 경우 병합(2번) 방식으로 진행"),
            "LGHV": ("O", "대사(1줄)+대사(1줄)만 가능. 하이픈+띄어쓰기"),
            "SKBB": ("X", ""),
            "JTBC": ("O", "대사(1줄)+대사(1줄)만 가능. 3인 이상 시 우선순위 작업 후 나머지 버림"),
            "TVCS": ("X", ""),
            "TVING": ("O", "대사+대사 / 대사+음향 등 조합 가능"),
        }),
        ("배경음악", "배경음악 별도 표기", {
            "DLIV": ("X", "배경음악 표기 없음"),
            "LGHV": ("O", "[배경음악] 표기"),
            "SKBB": ("X", ""), "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "[음악: '제목' OST] 또는 [ㅇㅇ한 음악] 표기. 제목은 티빙 제공 제목과 동일하게"),
        }),
        ("음향/효과음", "효과음 별도 표기", {
            "DLIV": ("O", "(ㅇㅇ 소리) 표기, (노래 전주) 표기"),
            "LGHV": ("O", "[ㅇㅇ 소리] 표기. 명확한 표현이 가능한 소리 (예: [휘파람 소리])"),
            "SKBB": ("O", "[ㅇㅇ 소리], [노래 전주], [웃음소리], [울음소리]"),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "명확/불명확 소리 표기 규칙. 화면에 보이면 미기입. 배경음 지속 시 [-계속]"),
        }),
        ("OC 자막 (100% 동일)", "OC 자막과 음성이 100% 동일한 경우 텍스트 작업", {
            "DLIV": ("X", "100% 동일한 경우 자막 생략"),
            "LGHV": ("\u25B3", "동일한 텍스트 작업 진행 (조건부)"),
            "SKBB": ("\u25B3", "동일한 텍스트 작업 진행 (조건부)"),
            "JTBC": ("X", "해당 부분 자막 삭제"),
            "TVCS": ("O", "동일한 텍스트 작업 진행"),
            "TVING": ("X", "동일한 텍스트 작업 진행"),
        }),
        ("OC 자막 (의미 동일)", "OC 자막과 음성의 의미가 동일한 경우 텍스트 작업", {
            "DLIV": ("O", ""), "LGHV": ("\u25B3", ""), "SKBB": ("\u25B3", ""),
            "JTBC": ("", ""), "TVCS": ("", ""), "TVING": ("", ""),
        }),
    ]),
    ("텍스트", [
        ("공통", "들리는 음성 기준 텍스트 수정. 문장부호 규칙·추임새 생략", {
            "DLIV": ("O", "마침표(.), 말줄임표(...), 물음표(?) 기입. 느낌표/물결/쉼표/인용 작은따옴표는 자제. 불필요한 추임새 생략 가능"),
            "LGHV": ("O", ""), "SKBB": ("O", ""), "JTBC": ("O", ""),
            "TVCS": ("O", ""), "TVING": ("O", ""),
        }),
        ("글자 수", "자막 한 줄당 최대 글자 수", {
            "DLIV": ("17글자", ""), "LGHV": ("18글자", ""), "SKBB": ("20글자", ""),
            "JTBC": ("18글자", ""), "TVCS": ("18글자", ""), "TVING": ("20글자", ""),
        }),
        ("줄 수", "자막당 최대 줄 수", {
            "DLIV": ("3줄", ""), "LGHV": ("2줄", ""), "SKBB": ("1줄", ""),
            "JTBC": ("2줄", ""), "TVCS": ("2줄", ""), "TVING": ("2줄", ""),
        }),
        ("노래 가사", "출연자가 실제 노래를 부르는 경우 별도 표기", {
            "DLIV": ("O", "OC 자막 존재 시 삭제. 일반 대사와 동일하게 표기"),
            "LGHV": ("O", "[노래 가사] 표기"),
            "SKBB": ("O", "최초 1회만 앞에 '-[노래]' 표기"),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "\u266A 노래가사 \u266A 표기"),
        }),
        ("화자 구분", "발화자가 변경된 경우 별도 표기", {
            "DLIV": ("O", "하이픈(-) 표기, 뒤 띄어쓰기 없음, 첫 발화부터. 예외) 해설: -(해설)V발화 / 3인 이상 동시발화: -(같이)V발화"),
            "LGHV": ("X", ""),
            "SKBB": ("O", "하이픈 표기 (띄어쓰기 X). 두 번째 발화자부터 기입"),
            "JTBC": ("X", ""), "TVCS": ("X", ""), "TVING": ("X", ""),
        }),
        ("비하인드/예고편", "콘텐츠 메인 앞뒤로 추가된 영상의 텍스트 작업", {
            "DLIV": ("O", "텍스트 작업과 동일하게 진행"),
            "LGHV": ("X", "해당 부분 자막 삭제"),
            "SKBB": ("O", "텍스트 작업과 동일하게 진행"),
            "JTBC": ("X", "해당 부분 자막 삭제"), "TVCS": ("X", "해당 부분 자막 삭제"),
            "TVING": ("O", "텍스트 작업과 동일하게 진행"),
        }),
        ("외국어 (문장)", "한국어가 아닌 외국어 문장의 텍스트 작업", {
            "DLIV": ("X", "샘플 내 사례 없음 → LGHV/SKBB 동일 가이드 적용 (외국어 문장 삭제)"),
            "LGHV": ("X", ""), "SKBB": ("X", ""), "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "[언어명]만 작성 (예: [영어])"),
        }),
        ("외국어 (단어 포함)", "한국어 대사 중 외국어 단어가 포함된 경우 텍스트 작업", {
            "DLIV": ("O", "한국어 문장 내 영어단어·스펠링은 표기. 영어 문장은 별도 표기 안 함"),
            "LGHV": ("O", ""), "SKBB": ("O", ""), "JTBC": ("O", ""),
            "TVCS": ("O", ""), "TVING": ("O", ""),
        }),
        ("묵음 처리", "비속어/상표 등 가공된 효과음 별도 표기", {
            "DLIV": ("X", "음절별 숫자 '0' 표기"),
            "LGHV": ("X", ""),
            "SKBB": ("O", "글자수 관계없이 2개의 별표(**) 표기"),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "삐 소리 음절마다 별표(*) 표기. 전체 문장 삐 처리는 [음소거 효과음]만 표기"),
        }),
    ]),
    ("배리어 프리", [
        ("화자 표기", "화면만으로 화자 식별 불가 시 화자 표기", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "텍스트 맨 앞에 (화자)+띄어쓰기 표기"),
        }),
        ("효과음 (편집 삽입)", "편집 시 삽입한 인위적 소리 별도 표기", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("X", ""), "TVCS": ("X", ""),
            "TVING": ("O", "[OO 효과음] 표기"),
        }),
        ("자막 위치", "OC 자막을 가리지 않게 자막 위치 변경", {
            "DLIV": ("X", ""), "LGHV": ("X", ""), "SKBB": ("X", ""),
            "JTBC": ("X", ""), "TVCS": ("X", ""), "TVING": ("X", ""),
        }),
    ]),
    ("수급 / 납품", [
        ("자막 형식", "최종 납품 자막의 파일 형식", {
            "DLIV": ("srt", ""), "LGHV": ("srt", ""), "SKBB": ("smi", ""),
            "JTBC": ("srt", ""), "TVCS": ("vtt", ""), "TVING": ("vtt", ""),
        }),
        ("마침표 삭제", "최종 납품 자막의 마침표 삭제 여부", {
            "DLIV": ("X", ""), "LGHV": ("O", ""), "SKBB": ("X", ""),
            "JTBC": ("O", ""), "TVCS": ("X", ""), "TVING": ("O", ""),
        }),
        ("수급 방식", "영상 파일 전달 방식", {
            "DLIV": ("구글 드라이브", "세팅 후 전달 예정"),
            "LGHV": ("구글 드라이브", ""), "SKBB": ("구글 드라이브", ""),
            "JTBC": ("", ""), "TVCS": ("", ""), "TVING": ("", ""),
        }),
        ("납품 방식", "자막 파일 전달 방식", {
            "DLIV": ("구글 드라이브", "세팅 후 전달 예정"),
            "LGHV": ("자체 프로그램", ""), "SKBB": ("이메일", ""),
            "JTBC": ("", ""), "TVCS": ("", ""), "TVING": ("", ""),
        }),
    ]),
]


# ── 정책 항목 ↔ 기술 항목 연결 (3번 페이지용) ──────────────────────
#   (정책 항목명, [기술항목 id …], 연결 설명)
ITEM_TECH_LINKS = [
    ("글자 수", ["s2c_vl_len", "s2_jtbc_pol", "s2_lghv_pol"], "줄별 길이 검증 및 글자수 초과 줄바꿈"),
    ("줄 수", ["s2c_vl_lnc"], "자막 줄 수 검증"),
    ("오버랩", ["s2_jtbc_vov", "s2_lghv_vov", "s2_skbb_vov", "s2_lghv_vot",
              "s2_skbb_vso", "s2_dliv_val", "s2_jtbc_pms", "s2_lghv_pms", "s2_dliv_pms"],
     "오버랩 줄수/존재 검증 및 다화자 병합 처리"),
    ("화자 구분", ["s2_skbb_vhy", "s2_dliv_vhy", "s2_skbb_pfh", "s2_skbb_psh", "s2_dliv_psh"],
     "하이픈 화자 표기 검증/처리"),
    ("노래 가사", ["s2_lghv_pmn", "s2_lghv_pkb", "s2_tvng_pmn"], "음표 표기 정규화"),
    ("음향/효과음", ["s2_lghv_pmn", "s2_tvng_pmn"], "음향/음표 표기 관련"),
    ("묵음 처리", ["s2_skbb_pas", "s2_skbb_vmo", "s2_skbb_pnp"], "별표/모자이크 처리·검증"),
    ("공통", ["s1_pp_wrp", "s1_pp_ell", "s1_vl_elip", "s2c_pp_asp"], "문장부호 정규화·검증"),
    ("외국어 (문장)", ["s2_skbb_vsc", "s1_vl_spec"], "특수문자/외국어 문자 검증"),
]


def seed(db: Session):
    if db.query(User).first():
        return

    # ── Users ── (기존 그대로)
    users = [
        User(id="u_admin", username="admin", hashed_password=hash_password("admin123"), name="관리자", role="admin"),
        User(id="u_dev1", username="dev1", hashed_password=hash_password("dev123"), name="개발팀 김철수", role="dev"),
        User(id="u_sub1", username="sub1", hashed_password=hash_password("sub123"), name="자막팀 이영희", role="subtitle"),
    ]
    db.add_all(users)

    # ── Broadcasters ── (기존 그대로)
    broadcasters = [
        Broadcaster(id="b_jtbc", code="JTBC", name="JTBC", color="#db2777"),
        Broadcaster(id="b_lghv", code="LGHV", name="LGHV", color="#dc2626"),
        Broadcaster(id="b_skbb", code="SKBB", name="SKBB", color="#f97316"),
        Broadcaster(id="b_tvcs", code="TVCS", name="TVCS", color="#8b5cf6"),
        Broadcaster(id="b_dliv", code="DLIV", name="DLIV", color="#3b82f6"),
        Broadcaster(id="b_tvng", code="TVNG", name="TVING", color="#b91c1c"),
    ]
    db.add_all(broadcasters)

    # ── Policy Matrix (NEW) ──
    item_lookup = {}          # 항목명 → PolicyItem
    value_lookup = {}         # (항목명, 방송사코드) → PolicyValue
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
                pv = PolicyValue(id=gen_id(), item_id=item.id, broadcaster_id=BC[code], summary=summary, detail=detail)
                db.add(pv)
                value_lookup[(item_name, code)] = pv
    db.flush()

    # 변경 이력 데모 (전/후 값 보존)
    demo = value_lookup.get(("글자 수", "DLIV"))
    if demo:
        db.add(PolicyValueHistory(id=gen_id(), value_id=demo.id, edited_by="u_sub1",
                                  old_summary="18글자", new_summary="17글자", note="DLIV 규격 변경 반영"))
    demo2 = value_lookup.get(("오버랩", "DLIV"))
    if demo2:
        db.add(PolicyValueHistory(id=gen_id(), value_id=demo2.id, edited_by="u_sub1",
                                  old_summary="X", new_summary="O", note="오버랩 작업 규칙 추가"))

    # ── Tech Items ── (기존 그대로)
    from app.seed_tech_items import get_tech_items
    tech_items = get_tech_items()
    for ti in tech_items:
        code = SOURCE_CODES.get(ti.function_name, "")
        if code:
            ti.source_code = code
    db.add_all(tech_items)
    db.flush()

    # ── Mappings ── (기존 그대로)
    stage1_ids = [ti.id for ti in tech_items if ti.stage == "stage1"]
    s2c_ids = [ti.id for ti in tech_items if ti.stage == "stage2" and ti.scope == "common"]
    s2s = {}
    for ti in tech_items:
        if ti.stage == "stage2" and ti.scope == "specific":
            parts = ti.id.split("_")
            if len(parts) >= 2:
                s2s.setdefault(parts[1], []).append(ti.id)

    bmap = {"b_jtbc": "jtbc", "b_lghv": "lghv", "b_skbb": "skbb", "b_tvcs": "tvcs", "b_dliv": "dliv", "b_tvng": "tvng"}
    for b in broadcasters:
        ids = list(stage1_ids) + list(s2c_ids) + s2s.get(bmap.get(b.id, ""), [])
        seen = set()
        for iid in ids:
            if iid not in seen:
                seen.add(iid)
                db.add(Mapping(id=gen_id(), broadcaster_id=b.id, item_id=iid))

    # ── Item ↔ Tech links (NEW) ──
    tech_ids = {ti.id for ti in tech_items}
    for item_name, tids, note in ITEM_TECH_LINKS:
        item = item_lookup.get(item_name)
        if not item:
            continue
        for tid in tids:
            if tid in tech_ids:
                db.add(ItemTechLink(id=gen_id(), policy_item_id=item.id, tech_item_id=tid, note=note))

    db.commit()
    print("✅ Seed data inserted successfully")