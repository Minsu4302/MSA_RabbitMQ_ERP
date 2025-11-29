from typing import Dict, Set

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


class ConnectionManager:
    """
    employeeId별 WebSocket 연결 관리.
    """
    def __init__(self) -> None:
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, employee_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(employee_id, set()).add(websocket)

    def disconnect(self, employee_id: int, websocket: WebSocket) -> None:
        conns = self.active_connections.get(employee_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self.active_connections.pop(employee_id, None)

    async def send_to_employee(self, employee_id: int, message: dict) -> None:
        conns = list(self.active_connections.get(employee_id, []))
        to_remove: list[WebSocket] = []

        for ws in conns:
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                to_remove.append(ws)
            except Exception:
                to_remove.append(ws)

        for ws in to_remove:
            self.disconnect(employee_id, ws)


manager = ConnectionManager()
