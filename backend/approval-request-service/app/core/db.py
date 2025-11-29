import os
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "erp")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "approvals")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """
    싱글톤 패턴으로 MongoDB 클라이언트 생성.
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client


def get_collection() -> AsyncIOMotorCollection:
    client = get_client()
    db = client[MONGODB_DB_NAME]
    return db[MONGODB_COLLECTION_NAME]


async def get_approvals_collection() -> AsyncGenerator[AsyncIOMotorCollection, None]:
    """
    FastAPI 의존성 주입용.
    """
    yield get_collection()
