import os

import aio_pika
from aio_pika import ExchangeType, Message
from fastapi import FastAPI

from app.schemas.message import ApprovalWorkMessage

RABBITMQ_EXCHANGE = "approval"
RABBITMQ_ROUTING_KEY = "approval.requested"
RABBITMQ_QUEUE = "approval.work"


def get_rabbitmq_url() -> str:
    return os.getenv("RABBITMQ_URL", "amqp://erpuser:erppassword@rabbitmq:5672/")


async def init_rabbitmq(app: FastAPI) -> None:
    url = get_rabbitmq_url()
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()

    exchange = await channel.declare_exchange(
        RABBITMQ_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)
    await queue.bind(exchange, routing_key=RABBITMQ_ROUTING_KEY)

    app.state.rabbit_connection = connection
    app.state.rabbit_channel = channel
    app.state.rabbit_exchange = exchange


async def close_rabbitmq(app: FastAPI) -> None:
    connection = getattr(app.state, "rabbit_connection", None)
    if connection:
        await connection.close()


async def publish_approval(app: FastAPI, msg: ApprovalWorkMessage) -> None:
    """
    ApprovalWorkMessage를 RabbitMQ로 publish.
    """
    exchange = app.state.rabbit_exchange
    body = msg.json().encode("utf-8")

    message = Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    await exchange.publish(message, routing_key=RABBITMQ_ROUTING_KEY)
