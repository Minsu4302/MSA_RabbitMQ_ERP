from pydantic import BaseModel
from fastapi import APIRouter

from app.core.connection_manager import manager

router = APIRouter(
    prefix="",
    tags=["notify"],
)


class NotificationPayload(BaseModel):
    employeeId: int
    type: str
    requestId: int | None = None
    step: int | None = None
    approverId: int | None = None
    finalStatus: str | None = None
    stepStatus: str | None = None
    title: str | None = None


@router.post("/notify", status_code=202)
async def notify(payload: NotificationPayload):
    """
    다른 서비스(Approval Request 등)가 호출하는 REST 엔드포인트.
    해당 employeeId의 모든 WebSocket 세션에 메시지 push.
    """
    await manager.send_to_employee(payload.employeeId, payload.model_dump())
    return {"delivered": True}
