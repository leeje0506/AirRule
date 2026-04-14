"""
초기 데이터 시드 스크립트.
DB 테이블 생성 후 자동 실행됩니다.
"""
from sqlalchemy.orm import Session
from app.models import User, Broadcaster, Policy, PolicyHistory, TechItem, Mapping, gen_id, utcnow
from app.auth import hash_password


def seed(db: Session):
    # Skip if already seeded
    if db.query(User).first():
        return

    # ── Users ──
    users = [
        User(id="u_admin", username="admin", hashed_password=hash_password("admin123"), name="관리자", role="admin"),
        User(id="u_dev1", username="dev1", hashed_password=hash_password("dev123"), name="개발팀 김철수", role="dev"),
        User(id="u_sub1", username="sub1", hashed_password=hash_password("sub123"), name="자막팀 이영희", role="subtitle"),
    ]
    db.add_all(users)

    # ── Broadcasters ──
    broadcasters = [
        Broadcaster(id="b_jtbc", code="jtbc", name="JTBC", color="#db2777"),
        Broadcaster(id="b_lgh", code="lgh", name="LG Hello", color="#dc2626"),
        Broadcaster(id="b_skb", code="skb", name="SK Btv", color="#f97316"),
        Broadcaster(id="b_csdi", code="csdi", name="CSDI", color="#3b82f6"),
        Broadcaster(id="b_tving", code="tving", name="TVING", color="#b91c1c"),
    ]
    db.add_all(broadcasters)

    # ── Policies ──
    policies = [
        Policy(
            id="pol_1", broadcaster_id="b_jtbc",
            title="JTBC 예능 제작 가이드라인", version="v2.4", status="active",
            rules={
                "specs": "18글자 / 2줄",
                "sync": "미탐지 대사 빈 싱크 추가. 반복 편집 시 횟수만큼 모두 작업.",
                "overlap": "3인 이상 오버랩 시 우선순위(중요도/화면노출) 작업 후 나머지 버림.",
                "lyrics": "대사 표기와 동일 방식 (OC 존재 시 삭제)",
                "foreign": "간단한 단어 한글 전사(버스, 티비). 문장 단위 외국어 삭제.",
                "sound": "배경음악 [배경음악] 표기. 음향/효과음 작업 없음.",
                "oc_delete": "음성과 동일한 OC 존재 시 삭제 (내용 일치 시)",
                "speaker": "화자 구분 작업 없음.",
                "punctuation": "문장구조 끝 마침표 필수. 단위기호는 한글 발음 표기(㎡ -> 제곱미터).",
            },
            created_by="u_sub1",
        ),
        Policy(
            id="pol_2", broadcaster_id="b_tving",
            title="TVING 오리지널 콘텐츠 규격", version="v3.1", status="active",
            rules={
                "specs": "17글자 / 3줄 (최대)",
                "sync": "시작 지점 정확하게 보정. 가독성 문제 시만 종료 지점 보정. 불필요 추임새 생략.",
                "overlap": "모든 자막 줄 수의 합이 3줄까지 가능. 중요한 발화 우선.",
                "lyrics": "♪ 노래가사 ♪ 표기",
                "foreign": "[언어명]만 작성 (예: [영어], [일어])",
                "sound": "화면만으로 알 수 없는 성대 발화 소리 [웃음소리] 등 표기. 지속 시 [-계속] 추가.",
                "oc_delete": "95% 동일 시 삭제. 예능 자막 스타일은 삭제 안 함.",
                "speaker": "동일OC 존재로 삭제 시 이어지는 자막 무조건 화자 표기.",
                "punctuation": "문장 끝 마침표(.) 필수. 느낌표/물결 사용 자제.",
            },
            created_by="u_sub1",
        ),
        Policy(
            id="pol_3", broadcaster_id="b_skb",
            title="Btv 영화 자막 송출 표준", version="v1.8", status="review",
            rules={
                "specs": "20글자 / 1줄",
                "sync": "싱크 길이 짧아서 읽기 불편하지 않도록 주의. 한국제작원 기준 준수.",
                "overlap": "대사(1줄)+대사(1줄)만 가능. 하이픈(-) 사용.",
                "lyrics": "최초 1회 앞에 -[노래] 표기.",
                "foreign": "OC자막 한국어 존재 시 그대로 작성. 외국어만 존재 시 삭제.",
                "sound": "맥락상 꼭 필요하며 화면 식별 불가 시만 [OO 소리] 표기.",
                "oc_delete": "음성과 동일 OC 존재 시 삭제 진행.",
                "speaker": "-(해설), -(같이) 등 하이픈 활용 표기.",
                "punctuation": "말줄임표(...), 물음표(?), 쉼표(,) 가능.",
            },
            created_by="u_sub1",
        ),
        Policy(id="pol_4", broadcaster_id="b_lgh", title="지역 채널 뉴스 자막 규정", version="v2.0", status="active", rules={}, created_by="u_sub1"),
        Policy(id="pol_5", broadcaster_id="b_csdi", title="CSDI 다큐멘터리 제작 규정", version="v0.9", status="draft", rules={}, created_by="u_sub1"),
    ]
    db.add_all(policies)

    # ── Policy History ──
    db.add_all([
        PolicyHistory(id=gen_id(), policy_id="pol_1", edited_by="u_sub1", summary="싱크 작업 규칙 수정: 반복 편집 시 횟수만큼 모두 작업 추가"),
        PolicyHistory(id=gen_id(), policy_id="pol_1", edited_by="u_sub1", summary="기본 규격 18글자로 변경"),
        PolicyHistory(id=gen_id(), policy_id="pol_2", edited_by="u_sub1", summary="오버랩 규칙 세분화"),
    ])

    # ── Tech Items ──
    tech_items = [
        TechItem(id="ti_p1", type="processing", name="Loudness Normalization", desc="오디오 신호의 평균 라우드니스를 표준 규격에 맞게 조정합니다.", params={"target": "-24 LKFS", "peak": "-1 dBTP", "mode": "True Peak"}, scope="common", tag="applied",
            source_code='''import numpy as np

def loudness_normalize(audio_data, target_lkfs=-24, peak_limit=-1):
    """오디오 라우드니스 정규화 처리"""
    current_loudness = measure_lkfs(audio_data)
    gain_db = target_lkfs - current_loudness
    normalized = apply_gain(audio_data, gain_db)
    
    # True Peak 리미팅
    peak = np.max(np.abs(normalized))
    if 20 * np.log10(peak) > peak_limit:
        normalized = true_peak_limit(normalized, peak_limit)
    
    return normalized, {
        "original_lkfs": current_loudness,
        "adjusted_lkfs": target_lkfs,
        "gain_applied": gain_db,
        "peak_limited": peak > 10 ** (peak_limit / 20)
    }
'''),
        TechItem(id="ti_p2", type="processing", name="AI UHD Upscaling", desc="FHD 소스를 UHD 해상도로 정밀 업스케일링합니다.", params={"model": "v4-high-fidelity", "sharpness": "0.4", "denoise": "true"}, scope="specific", tag="applied",
            source_code='''import torch
from models.upscaler import UHDUpscaler

def upscale_to_uhd(frame, model_name="v4-high-fidelity", sharpness=0.4, denoise=True):
    """FHD 프레임을 UHD로 업스케일링"""
    model = UHDUpscaler.load(model_name)
    
    if denoise:
        frame = apply_denoise(frame, strength=0.3)
    
    upscaled = model.predict(frame)
    
    if sharpness > 0:
        upscaled = unsharp_mask(upscaled, amount=sharpness)
    
    return upscaled
'''),
        TechItem(id="ti_p3", type="processing", name="Frame Rate Conversion", desc="영상 프레임을 타겟 송출 규격에 맞게 보간합니다.", params={"target_fps": "29.97", "method": "optical_flow"}, scope="common", tag="in_progress",
            source_code='''from video_utils import optical_flow_interpolate

def convert_frame_rate(video_stream, target_fps=29.97, method="optical_flow"):
    """프레임 레이트 변환"""
    src_fps = video_stream.fps
    
    if abs(src_fps - target_fps) < 0.01:
        return video_stream  # 변환 불필요
    
    if method == "optical_flow":
        result = optical_flow_interpolate(video_stream, target_fps)
    elif method == "blend":
        result = frame_blend(video_stream, target_fps)
    else:
        result = nearest_frame(video_stream, target_fps)
    
    return result
'''),
        TechItem(id="ti_v1", type="validation", name="Char Limit Validator", desc="방송사별 설정된 글자 수 및 줄 수 제한 위반을 실시간 검출합니다.", params={"mode": "strict", "ignore_space": "false"}, scope="common", tag="applied",
            source_code='''import re

def validate_char_limit(srt_entries, max_chars=18, max_lines=2, mode="strict", ignore_space=False):
    """자막 글자 수 / 줄 수 제한 검증"""
    errors = []
    
    for entry in srt_entries:
        lines = entry["text"].split("\\n")
        
        # 줄 수 체크
        if len(lines) > max_lines:
            errors.append({
                "index": entry["index"],
                "type": "LINE_OVERFLOW",
                "message": f"줄 수 초과: {len(lines)}줄 (최대 {max_lines}줄)",
                "severity": "error",
                "timecode": entry["timecode"]
            })
        
        # 글자 수 체크
        for i, line in enumerate(lines):
            text = line if not ignore_space else line.replace(" ", "")
            if len(text) > max_chars:
                errors.append({
                    "index": entry["index"],
                    "type": "CHAR_OVERFLOW",
                    "message": f"글자 수 초과: {len(text)}자 (최대 {max_chars}자) - Line {i+1}",
                    "severity": "error" if mode == "strict" else "warning",
                    "timecode": entry["timecode"],
                    "line": i + 1,
                    "text": text
                })
    
    return {
        "passed": len(errors) == 0,
        "total_entries": len(srt_entries),
        "error_count": len(errors),
        "errors": errors
    }
'''),
        TechItem(id="ti_v2", type="validation", name="Gamut Error Check", desc="Rec.709/2020 색역을 벗어나는 픽셀을 검출합니다.", params={"standard": "Rec.709", "threshold": "5%"}, scope="common", tag="applied",
            source_code='''import numpy as np
from colorspace import check_gamut

def validate_gamut(frame_data, standard="Rec.709", threshold=0.05):
    """색역 범위 검증"""
    out_of_gamut = check_gamut(frame_data, standard)
    ratio = np.sum(out_of_gamut) / frame_data.size
    
    return {
        "passed": ratio <= threshold,
        "out_of_gamut_ratio": f"{ratio*100:.2f}%",
        "threshold": f"{threshold*100:.1f}%",
        "standard": standard,
        "pixel_count": int(np.sum(out_of_gamut))
    }
'''),
        TechItem(id="ti_v3", type="validation", name="OC Similarity Scan", desc="영상 내 원본 자막(OC)과 전사 텍스트의 일치율을 분석합니다.", params={"min_match": "95%", "engine": "OCR-v3"}, scope="specific", tag="planned",
            source_code='''from ocr_engine import extract_text_from_frame
from difflib import SequenceMatcher

def scan_oc_similarity(srt_entries, video_frames, min_match=0.95, engine="OCR-v3"):
    """OC 자막과 전사 텍스트 유사도 분석"""
    results = []
    
    for entry in srt_entries:
        frame = get_frame_at(video_frames, entry["start_time"])
        oc_text = extract_text_from_frame(frame, engine=engine)
        
        if oc_text:
            similarity = SequenceMatcher(None, entry["text"], oc_text).ratio()
            results.append({
                "index": entry["index"],
                "srt_text": entry["text"],
                "oc_text": oc_text,
                "similarity": f"{similarity*100:.1f}%",
                "should_delete": similarity >= min_match,
                "timecode": entry["timecode"]
            })
    
    return {
        "total_compared": len(results),
        "delete_candidates": sum(1 for r in results if r["should_delete"]),
        "results": results
    }
'''),
    ]
    db.add_all(tech_items)

    # ── Mappings ──
    mapping_data = {
        "b_jtbc": ["ti_p1", "ti_p3", "ti_v1", "ti_v2"],
        "b_tving": ["ti_p1", "ti_p2", "ti_p3", "ti_v1", "ti_v2", "ti_v3"],
        "b_skb": ["ti_p1", "ti_p3", "ti_v1", "ti_v2"],
        "b_lgh": ["ti_p1", "ti_v1"],
        "b_csdi": ["ti_p1", "ti_p3", "ti_v1", "ti_v2"],
    }
    for b_id, item_ids in mapping_data.items():
        for item_id in item_ids:
            db.add(Mapping(id=gen_id(), broadcaster_id=b_id, item_id=item_id))

    db.commit()
    print("✅ Seed data inserted successfully")
