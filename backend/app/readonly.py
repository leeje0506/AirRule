"""
읽기 전용 가드.

메모리 DB 로 뜬 배포에서는 저장해도 서버가 내려갈 때 사라진다.
"성공했는데 조용히 사라지는" 상황을 만들지 않으려고 쓰기 요청을 명시적으로 막는다.
편집이 필요해지면 AIRRULE_DATABASE_URL 로 영속 DB 를 주면 자동으로 풀린다.
"""
from fastapi import HTTPException

from app.database import READ_ONLY

MESSAGE = (
    "읽기 전용 배포입니다. 방송사 규칙은 config_subtitle.yml, "
    "정책 매트릭스는 seed.py 에서 관리하고 재배포로 반영합니다."
)


def guard_write():
    """쓰기 엔드포인트 맨 앞에서 호출한다."""
    if READ_ONLY:
        raise HTTPException(status_code=503, detail=MESSAGE)
