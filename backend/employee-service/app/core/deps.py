from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import Depends
from app.core.config import settings  # 이제 settings는 config에서 가져옵니다.

# SQLAlchemy 비동기 엔진 생성
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL, echo=True)

# 비동기 세션 생성기
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 의존성으로 DB 세션을 반환하는 함수
async def get_db() -> AsyncSession:
    """
    DB 세션을 생성하여 yield 하고, 사용 후 닫아줍니다.
    AsyncSessionLocal 자체가 가변 키워드 인자를 받는 callable이라
    FastAPI가 이를 검사해 잘못된 query parameter(local_kw)를
    OpenAPI에 추가하는 문제가 있어, 여기서 직접 세션을 생성합니다.
    """
    async with AsyncSessionLocal() as session:
        yield session
