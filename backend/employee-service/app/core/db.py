import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# 환경변수에서 DB 설정 읽기 (없으면 기본값 사용)
MYSQL_USER = os.getenv("MYSQL_USER", "erpuser")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "erppassword")
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "erp")

DATABASE_URL = (
    f"mysql+asyncmy://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

# SQLAlchemy Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,          # 개발용: 실행되는 SQL 로그 찍기 (트러블슈팅에 도움)
    future=True,
)

# 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)

# Base 클래스 (모든 모델의 부모)
Base = declarative_base()


# FastAPI 의존성 주입용 세션
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    """
    애플리케이션 시작 시 한 번 호출해서
    employees 테이블 등 SQLAlchemy 모델 기반 테이블을 생성.
    이미 있으면 아무 일도 안 함 (CREATE TABLE IF NOT EXISTS 느낌).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)