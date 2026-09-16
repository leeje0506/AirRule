"""
DB 연결.

기본은 **메모리 SQLite** 다. 이 서비스가 보여주는 데이터(방송사·기술항목·매핑·연결)는
전부 config_subtitle.yml 과 policy 정의 파일에서 파생되므로 보관할 상태가 없다.
서버가 뜰 때 시드가 메모리에 채워 넣고, 내려가면 같이 사라진다.
덕분에 파일 쓰기가 불가능한 서버리스(Vercel 등)에서도 그대로 돈다.

영속 저장이 필요해지면 AIRRULE_DATABASE_URL 을 주면 된다.
  sqlite:///./airrule.db            로컬 파일
  postgresql+psycopg://user:pw@host/db
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("AIRRULE_DATABASE_URL", "").strip()

if DATABASE_URL:
    IN_MEMORY = DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    # 메모리 SQLite 는 연결마다 빈 DB 가 새로 생긴다.
    # StaticPool 로 연결 하나를 공유해야 모든 세션이 같은 데이터를 본다.
    IN_MEMORY = True
    DATABASE_URL = "sqlite://"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

# 메모리 모드면 저장해도 서버가 내려갈 때 사라지므로 쓰기를 막는다.
READ_ONLY = os.environ.get("AIRRULE_READ_ONLY", "auto").lower()
READ_ONLY = IN_MEMORY if READ_ONLY == "auto" else READ_ONLY in ("1", "true", "yes")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
