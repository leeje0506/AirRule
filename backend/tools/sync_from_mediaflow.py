"""
mediaflow 원본에서 AirRule 서비스로 규칙을 동기화한다.

생성물 (둘 다 self-contained — 실행 시 mediaflow / yaml 의존 없음):
  backend/app/engine/rules.py      ← utils/subtitle/rules/*.py 병합 (+ subtitle_common shim)
  backend/app/pipeline_config.py   ← config/config_subtitle.yml 전사

Usage:
    python backend/tools/sync_from_mediaflow.py /path/to/mediaflow
"""
import ast
import os
import re
import pprint
import sys
from datetime import date

# 병합 순서 = mediaflow utils/subtitle/rules/__init__.py 의 import 순서.
# 뒤에 오는 모듈이 같은 이름의 함수를 덮어쓴다 (postprocess_sync_overlap,
# validate_special_characters_allow_music_note 는 stage2 판이 유효).
# postprocess_final 은 __init__ 에 없지만 납품 단계(subtitle_final_processor)가
# 직접 호출하므로 마지막에 둬서 remove_last_punctuation / add_banner 를 최종판으로 만든다.
MODULES = [
    ("validate_common.py", "공통 검증"),
    ("postprocess_common.py", "공통 후처리 (1차 · 2차 공용)"),
    ("postprocess_stage2.py", "2차 후처리"),
    ("validate_stage2.py", "2차 검증"),
    ("postprocess_final.py", "최종 납품 후처리"),
]

HEADER = '''"""
AirRule 테스트 엔진 — mediaflow utils/subtitle/rules/* 원본 이식본.

⚠️  이 파일은 backend/tools/sync_from_mediaflow.py 가 생성합니다. 직접 수정하지 마세요.
    mediaflow 원본: @MODULES@
    동기화 날짜: @TODAY@

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

STYLE_TAG_PATTERN = re.compile(r"\\{\\\\[^}]*\\}")


def strip_style_tags(text: str) -> str:
    """스타일 태그({\\\\an8} 등) 제거 — 글자 수 측정용."""
    if not text:
        return text or ""
    return STYLE_TAG_PATTERN.sub("", text)


def replace_linebreak(content: str, rep_char: str = " ") -> str:
    if content is None:
        return ""
    return content.replace("\\n", rep_char)


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
'''


# 함수 안에서 다시 import 하는 자리 — 병합된 이 모듈 안에 이미 같은 이름이 있으므로
# 주석 처리한다. (남겨두면 실행 시 ModuleNotFoundError: No module named 'utils')
LOCAL_IMPORT_RE = re.compile(r"^(\s*)from utils\.[\w.]+ import (.+)$", re.MULTILINE)


def _drop_local_imports(source):
    return LOCAL_IMPORT_RE.sub(
        lambda m: f"{m.group(1)}# (이식) from utils… import {m.group(2)}"
                  f" — 이 모듈에 이미 정의되어 있음",
        source,
    )


def extract_functions(path):
    """모듈 최상위 def 를 (이름, 소스) 순서대로 추출."""
    src = open(path, encoding="utf-8").read()
    out = []
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef):
            out.append((node.name, _drop_local_imports(ast.get_source_segment(src, node))))
    return out


def build_rules(mediaflow_dir, dest):
    rules_dir = os.path.join(mediaflow_dir, "utils", "subtitle", "rules")
    chunks = [
        HEADER.replace("@MODULES@", ", ".join(m for m, _ in MODULES))
        .replace("@TODAY@", date.today().isoformat())
    ]
    seen = {}
    for filename, label in MODULES:
        funcs = extract_functions(os.path.join(rules_dir, filename))
        chunks.append(
            "\n\n# ============================================================\n"
            f"# {label}  ({filename})\n"
            "# ============================================================\n"
        )
        for name, source in funcs:
            if name in seen:
                chunks.append(f"\n# NOTE: {name} — {seen[name]} 판을 덮어씀 (mediaflow import 순서와 동일)\n")
            seen[name] = filename
            chunks.append("\n" + source + "\n")

    with open(dest, "w", encoding="utf-8") as f:
        f.write("".join(chunks))
    return len(seen)


CONFIG_HEADER = '''"""
config/config_subtitle.yml 전사본 (mediaflow 파이프라인 설정).

⚠️  이 파일은 backend/tools/sync_from_mediaflow.py 가 생성합니다. 직접 수정하지 마세요.
    동기화 날짜: @TODAY@

- VALIDATION_PARAMS : 방송사별 글자 수 / 줄 수 / 바이트 / 가중치
- STAGE1 / STAGE2   : 실행 순서 그대로의 후처리 · 검증 목록
                      (STAGE2 방송사 항목의 *_extend 는 공통 뒤에 이어 붙고,
                       *_remove 에 적힌 함수는 공통에서 빠진다)
- FINAL             : 납품 확장자 · 마침표 제거 · 배너
"""

'''


def build_config(mediaflow_dir, dest):
    import yaml

    path = os.path.join(mediaflow_dir, "config", "config_subtitle.yml")
    data = yaml.safe_load(open(path, encoding="utf-8"))["subtitle"]

    def dump(name, value):
        return f"{name} = " + pprint.pformat(value, width=100, sort_dicts=False) + "\n\n"

    body = CONFIG_HEADER.replace("@TODAY@", date.today().isoformat())
    body += dump("VALIDATION_PARAMS", data["validation_params"])
    body += dump("STAGE1", data["stage1"])
    body += dump("STAGE2", data["stage2"])
    body += dump("FINAL", data["final_postprocess"])
    body += (
        "# 방송사 코드 (config 에 등장하는 순서)\n"
        "BROADCASTER_CODES = "
        + pprint.pformat([k for k in data["stage2"] if k != "common"], width=100)
        + "\n"
    )
    with open(dest, "w", encoding="utf-8") as f:
        f.write(body)
    return len(data["stage2"]) - 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src_dir = sys.argv[1]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
    n_fn = build_rules(src_dir, os.path.join(here, "app", "engine", "rules.py"))
    n_bc = build_config(src_dir, os.path.join(here, "app", "pipeline_config.py"))
    print(f"rules.py: 함수 {n_fn}개 / pipeline_config.py: 방송사 {n_bc}개")
