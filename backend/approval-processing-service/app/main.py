import logging

from fastapi import FastAPI

from app.api.process import router as process_router
from app.core.rabbitmq import start_consumer, close_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Approval Processing Service",
    version="0.1.0",
    description="REST + RabbitMQ consumer + In-Memory Queue for approvals",
)

# REST 라우터 등록
app.include_router(process_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "approval-processing-service",
    }


@app.get("/")
async def root():
    return {
        "message": "Approval Processing Service is running",
        "docs": "/docs",
    }


@app.on_event("startup")
async def on_startup():
    logger.info("Starting RabbitMQ consumer for Approval Processing Service")
    await start_consumer(app)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down RabbitMQ consumer for Approval Processing Service")
    await close_consumer(app)
