import json
import os

import aio_pika
from aio_pika import IncomingMessage
from fastapi import FastAPI

from app.core.queue import WorkItem, approval_queue

RABBITMQ_QUEUE = "approval.work"


def get_rabbitmq_url() -> str:
    return os.getenv("RABBITMQ_URL", "amqp://erpuser:erppassword@rabbitmq:5672/")


async def _handle_message(message: IncomingMessage) -> None:
    """
    Approval Request Service에서 publish한 ApprovalWorkMessage를 수신하여,
    현재 pending인 step 중 가장 앞의 step에 대해 WorkItem을 생성한다.
    """
    async with message.process():  # 예외 없으면 ack
        try:
            data = json.loads(message.body.decode("utf-8"))
        except json.JSONDecodeError:
            print("[RabbitMQ] Invalid JSON message:", message.body)
            return

        steps = data.get("steps", [])
        pending_steps = [s for s in steps if s.get("status") == "pending"]
        if not pending_steps:
            # 남은 pending step이 없으면 WorkItem 생성 X
            return

        # step 번호가 가장 작은 pending step 선택 (순차 결재)
        current = sorted(pending_steps, key=lambda s: s["step"])[0]

        item = WorkItem(
            request_id=data["requestId"],
            step=current["step"],
            requester_id=data["requesterId"],
            approver_id=current["approverId"],
            title=data["title"],
            content=data["content"],
            status="pending",
        )
        approval_queue.enqueue(item)
        print(f"[RabbitMQ] WorkItem added for approver {item.approver_id}: {item}")


async def start_consumer(app: FastAPI) -> None:
    url = get_rabbitmq_url()
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()

    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)
    await queue.consume(_handle_message)

    app.state.rabbit_connection = connection
    app.state.rabbit_channel = channel

    print("[RabbitMQ] Consumer started")


async def close_consumer(app: FastAPI) -> None:
    connection = getattr(app.state, "rabbit_connection", None)
    if connection:
        await connection.close()
        print("[RabbitMQ] Consumer connection closed")
