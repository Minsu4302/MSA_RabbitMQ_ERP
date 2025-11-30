from fastapi import FastAPI

from app.api.employees import router as employees_router
from app.api.attendance import router as attendance_router
from app.api.leaves import router as leaves_router
from app.core.db import init_db

app = FastAPI(
    title="Employee Service",
    version="0.1.0",
    description="Employee CRUD service (REST + MySQL + SQLAlchemy)",
)

@app.on_event("startup")
async def on_startup() -> None:
    # MySQL에 employees 테이블 등 생성
    await init_db()

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "employee-service",
    }


@app.get("/")
async def root():
    return {
        "message": "Employee Service is running",
        "docs": "/docs",
    }

app.include_router(employees_router)
app.include_router(employees_router)
app.include_router(attendance_router)
app.include_router(leaves_router)