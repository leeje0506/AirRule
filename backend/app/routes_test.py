"""
테스트 파이프라인 API
SRT를 입력받아 선택된 후처리/검증 항목을 순서대로 실행(시뮬레이션)하고 결과를 반환합니다.
실제 코드 실행은 추후 연동 — 현재는 mock 결과를 생성합니다.
"""
import re
import random
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TechItem
from app.auth import get_current_user

router = APIRouter(prefix="/api/test", tags=["test"])


class TestRunRequest(BaseModel):
    srt_text: str
    broadcaster_id: str
    pipeline: list[str]  # ordered list of tech item IDs
    params_override: dict = {}  # { item_id: { param_key: value } }


def parse_srt(text: str) -> list[dict]:
    """SRT 텍스트를 파싱하여 엔트리 리스트로 변환"""
    entries = []
    blocks = re.split(r'\n\s*\n', text.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        timecode = lines[1].strip()
        content = '\n'.join(lines[2:])
        entries.append({
            "index": index,
            "timecode": timecode,
            "text": content,
        })
    return entries


def mock_char_limit_validation(entries: list[dict], params: dict) -> dict:
    """글자 수/줄 수 검증 시뮬레이션"""
    max_chars = 18
    max_lines = 2
    # Parse specs like "18글자 / 2줄" from params
    mode = params.get("mode", "strict")
    ignore_space = params.get("ignore_space", "false") == "true"

    errors = []
    for entry in entries:
        text_lines = entry["text"].split("\n")
        if len(text_lines) > max_lines:
            errors.append({
                "index": entry["index"],
                "type": "LINE_OVERFLOW",
                "severity": "error",
                "message": f"줄 수 초과: {len(text_lines)}줄 (최대 {max_lines}줄)",
                "timecode": entry["timecode"],
                "text": entry["text"],
            })
        for i, line in enumerate(text_lines):
            check_text = line if not ignore_space else line.replace(" ", "")
            if len(check_text) > max_chars:
                errors.append({
                    "index": entry["index"],
                    "type": "CHAR_OVERFLOW",
                    "severity": "error" if mode == "strict" else "warning",
                    "message": f"글자 수 초과: {len(check_text)}자 (최대 {max_chars}자) - Line {i+1}",
                    "timecode": entry["timecode"],
                    "text": line,
                    "char_count": len(check_text),
                    "limit": max_chars,
                })
    return {
        "passed": len(errors) == 0,
        "total_entries": len(entries),
        "error_count": len(errors),
        "errors": errors,
    }


def mock_processing_result(item_name: str, entries: list[dict]) -> dict:
    """후처리 항목의 시뮬레이션 결과"""
    return {
        "passed": True,
        "total_entries": len(entries),
        "error_count": 0,
        "errors": [],
        "info": f"{item_name} 처리 완료 — {len(entries)}개 엔트리 처리됨",
    }


def mock_validation_result(item_name: str, entries: list[dict]) -> dict:
    """일반 검증 항목의 시뮬레이션 결과 (일부 랜덤 오류 생성)"""
    errors = []
    # 랜덤으로 0~2개 오류 생성
    sample_count = min(random.randint(0, 2), len(entries))
    if sample_count > 0:
        samples = random.sample(entries, sample_count)
        for entry in samples:
            errors.append({
                "index": entry["index"],
                "type": "VALIDATION_ISSUE",
                "severity": random.choice(["warning", "error"]),
                "message": f"{item_name} 검증 이슈 발견",
                "timecode": entry["timecode"],
                "text": entry["text"],
            })
    return {
        "passed": len(errors) == 0,
        "total_entries": len(entries),
        "error_count": len(errors),
        "errors": errors,
    }


@router.post("/run")
def run_test_pipeline(body: TestRunRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # Parse SRT
    entries = parse_srt(body.srt_text)
    if not entries:
        return {"error": "SRT 파싱 실패: 유효한 자막 엔트리가 없습니다.", "steps": []}

    # Load items in pipeline order
    items_map = {}
    if body.pipeline:
        all_items = db.query(TechItem).filter(TechItem.id.in_(body.pipeline)).all()
        items_map = {item.id: item for item in all_items}

    steps = []
    current_entries = entries  # 파이프라인을 거치며 변환될 수 있음

    for step_index, item_id in enumerate(body.pipeline):
        item = items_map.get(item_id)
        if not item:
            steps.append({
                "step": step_index + 1,
                "item_id": item_id,
                "item_name": "Unknown",
                "item_type": "unknown",
                "status": "error",
                "result": {"passed": False, "error_count": 1, "errors": [{"message": "항목을 찾을 수 없습니다."}]},
            })
            continue

        # 파라미터 오버라이드 적용
        effective_params = dict(item.params or {})
        if item_id in body.params_override:
            effective_params.update(body.params_override[item_id])

        # 항목 타입별 시뮬레이션
        if item.name == "Char Limit Validator":
            result = mock_char_limit_validation(current_entries, effective_params)
        elif item.type == "processing":
            result = mock_processing_result(item.name, current_entries)
        else:
            result = mock_validation_result(item.name, current_entries)

        steps.append({
            "step": step_index + 1,
            "item_id": item.id,
            "item_name": item.name,
            "item_type": item.type,
            "params_used": effective_params,
            "status": "pass" if result.get("passed", True) else "fail",
            "result": result,
        })

    # Summary
    total_errors = sum(s["result"].get("error_count", 0) for s in steps)
    all_passed = all(s["status"] == "pass" for s in steps)

    return {
        "srt_entry_count": len(entries),
        "pipeline_length": len(body.pipeline),
        "all_passed": all_passed,
        "total_errors": total_errors,
        "entries": entries,  # 원본 파싱 결과도 함께 반환
        "steps": steps,
    }
