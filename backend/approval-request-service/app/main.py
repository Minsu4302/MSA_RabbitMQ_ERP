from fastapi import FastAPI

from app.api.approvals import router as approvals_router
from app.core.rabbitmq import init_rabbitmq, close_rabbitmq

app = FastAPI(
    title="Approval Request Service",
    version="0.1.0",
    description="Approval Request Service (REST + MongoDB + RabbitMQ producer)",
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "approval-request-service",
    }


@app.get("/")
async def root():
    return {
        "message": "Approval Request Service is running",
        "docs": "/docs",
    }


@app.on_event("startup")
async def on_startup():
    # 1) (옵션) DB 초기화
    # await init_db()
    # 2) RabbitMQ 연결
    await init_rabbitmq(app)


@app.on_event("shutdown")
async def on_shutdown():
    await close_rabbitmq(app)


app.include_router(approvals_router)
