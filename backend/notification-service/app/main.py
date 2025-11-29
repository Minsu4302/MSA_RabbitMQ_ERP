from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect

from app.api.notify import router as notify_router
from app.core.connection_manager import manager

app = FastAPI(
    title="Notification Service",
    version="0.1.0",
    description="WebSocket notification service for approval results",
)

app.include_router(notify_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "notification-service"}


@app.websocket("/ws/{employee_id}")
async def websocket_endpoint(websocket: WebSocket, employee_id: int):
    """
    클라이언트(프론트)가 employee_id로 접속하는 WebSocket 엔드포인트.
    예: ws://localhost:8004/ws/2
    """
    await manager.connect(employee_id, websocket)
    try:
        while True:
            # 클라이언트에서 오는 메시지는 지금은 무시(keep-alive 용)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(employee_id, websocket)
