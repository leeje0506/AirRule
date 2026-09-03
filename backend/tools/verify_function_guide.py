"""
frontend/src/data/functionGuide.js 의 예시를 실제 엔진(app.engine.rules)에 돌려 검증한다.

가이드가 엔진과 어긋나면 화면 설명이 거짓말이 되므로, 예시를 고칠 때마다 돌린다.
시간·다중 자막이 필요한 함수는 자동 검증 대상이 아니라서 SKIP 으로 보고한다.

Usage:
    python backend/tools/verify_function_guide.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.engine import rules  # noqa: E402

GUIDE_JS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "src", "data", "functionGuide.js",
)

# 자동 검증할 때 넣어줄 파라미터 (config 의 대표값)
PARAMS = {
    "postprocess_over_length_lines": {"max_length": 18},
    "postprocess_over_length_lines_middle": {"max_length": 18},
    "postprocess_remove_first_hypn": {"punctuation": "-", "subtitle_index": 1},
    "validate_ellipsis_count": {"criterion": 5},
    "validate_length_lines": {"max_length": 18, "valid_type": "length"},
    "validate_line_count": {"max_lines": 2},
    "validate_line_count_allow_hyphen": {"max_lines": 1, "max_lines_with_hyphen": 2},
    "validate_mosaic_count_for_skbb": {"criterion": 2},
}

# 예시가 문장이 아니라 상황 설명(싱크·다중 자막)이라 문자열로 돌릴 수 없는 함수
NOT_TEXT_LEVEL = {
    "postprocess_remove_delete_tag",
    "postprocess_sync_overlap",
    "postprocess_reset_subtitles_from_list",
    "postprocess_mark_overlapped_multi_speaker",
    "postprocess_apply_overlap_hyphen_for_all_speech",
    "postprocess_add_period_between_subs",
    "postprocess_adjust_subtitle_gaps",
    "postprocess_adjust_short_sync",
    "postprocess_add_banner_subtitle",
    "validate_sync_negative_or_zero",
    "validate_sync_overlapped",
    "validate_sync_short_duration",
    "validate_sync_gap",
    "validate_overlapped_over_lines",
    "validate_overlapped_only_text_for_lghv",
    "validate_overlapped_accumulated_lines",
}


def load_guide():
    """JS 객체 리터럴을 node 로 JSON 화해서 읽는다."""
    src = open(GUIDE_JS, encoding="utf-8").read()
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
        f.write(src.replace("export const", "const").replace("export function", "function"))
        f.write("\nprocess.stdout.write(JSON.stringify(FUNCTION_GUIDE));\n")
        tmp = f.name
    try:
        return json.loads(subprocess.check_output(["node", tmp], text=True))
    finally:
        os.unlink(tmp)


def unescape(text):
    """가이드에 화면용으로 적힌 \\n 을 실제 줄바꿈으로."""
    return text.replace("\\n", "\n")


def main():
    guide = load_guide()
    ok = fail = skip = 0
    problems = []

    for fn_name, entry in guide.items():
        fn = getattr(rules, fn_name, None)
        if fn is None:
            problems.append(f"[없는 함수] {fn_name}")
            fail += 1
            continue
        if fn_name in NOT_TEXT_LEVEL:
            skip += len(entry.get("cases", []))
            continue

        params = PARAMS.get(fn_name, {})
        for case in entry.get("cases", []):
            if "before" in case:
                got = fn(unescape(case["before"]), **params)
                want = unescape(case["after"])
                if got == want:
                    ok += 1
                else:
                    fail += 1
                    problems.append(
                        f"[불일치] {fn_name} / {case.get('label')}\n"
                        f"    입력  {unescape(case['before'])!r}\n"
                        f"    가이드 {want!r}\n"
                        f"    실제  {got!r}"
                    )
            elif "input" in case:
                got = bool(fn(unescape(case["input"]), **params))
                if got == case["fail"]:
                    ok += 1
                else:
                    fail += 1
                    problems.append(
                        f"[불일치] {fn_name} / {case.get('label')}\n"
                        f"    입력  {unescape(case['input'])!r}\n"
                        f"    가이드 fail={case['fail']} / 실제 fail={got}"
                    )

    for p in problems:
        print(p)
    print(f"\n일치 {ok} / 불일치 {fail} / 검증 제외(싱크·다중자막) {skip}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
