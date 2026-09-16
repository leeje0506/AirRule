"""
로그인 계정.

계정을 코드에 두면 공개 리포·공개 URL 에 그대로 노출된다.
AIRRULE_USERS 환경변수로 넘기고, 소스에는 로컬 개발용 기본값만 남긴다.

형식 (JSON 배열):
    AIRRULE_USERS='[{"username":"admin","password":"...","name":"관리자","role":"admin"}]'

role 은 admin | dev | subtitle. 현재 배포는 읽기 전용이라 역할은 화면 표시용이다.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

# 로컬 개발 전용. 배포 환경에서는 쓰이지 않는다(아래에서 막는다).
DEV_USERS = [
    {"username": "admin", "password": "admin123", "name": "관리자", "role": "admin"},
    {"username": "dev1", "password": "dev123", "name": "개발팀 김철수", "role": "dev"},
    {"username": "sub1", "password": "sub123", "name": "자막팀 이영희", "role": "subtitle"},
]

REQUIRED_KEYS = {"username", "password", "name", "role"}


class AccountConfigError(RuntimeError):
    pass


def _parse(raw: str):
    try:
        users = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AccountConfigError(f"AIRRULE_USERS 가 올바른 JSON 이 아닙니다: {e}") from e

    if not isinstance(users, list) or not users:
        raise AccountConfigError("AIRRULE_USERS 는 비어 있지 않은 JSON 배열이어야 합니다.")

    for u in users:
        missing = REQUIRED_KEYS - set(u or {})
        if missing:
            raise AccountConfigError(f"AIRRULE_USERS 항목에 {sorted(missing)} 가 없습니다.")
    return users


def get_users():
    """(username, password, name, role) 목록을 반환한다."""
    raw = os.environ.get("AIRRULE_USERS", "").strip()
    if raw:
        return _parse(raw)

    # Vercel 등 배포 환경에서 기본 계정이 나가는 것을 막는다.
    if os.environ.get("VERCEL") or os.environ.get("AIRRULE_ENV") == "production":
        raise AccountConfigError(
            "AIRRULE_USERS 가 설정되지 않았습니다. 배포 환경에서는 계정을 "
            "환경변수로 넘겨야 합니다. 예: "
            '[{"username":"...","password":"...","name":"...","role":"admin"}]'
        )

    logger.warning(
        "AIRRULE_USERS 가 없어 로컬 개발용 기본 계정을 사용합니다. 배포에서는 반드시 설정하세요."
    )
    return DEV_USERS
