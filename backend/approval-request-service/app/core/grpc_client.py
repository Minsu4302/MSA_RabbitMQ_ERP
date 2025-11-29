import logging
import os
from typing import Any, Dict

import grpc

from app.grpc_stubs import approval_pb2, approval_pb2_grpc

logger = logging.getLogger(__name__)

APPROVAL_PROCESSING_GRPC_TARGET = os.getenv(
    "APPROVAL_PROCESSING_GRPC_TARGET",
    "approval-processing-service:50051",
)


async def send_approval_request(doc: Dict[str, Any]) -> None:
    """
    MongoDB에 저장된 approval document를 기반으로
    Approval Processing Service에 gRPC RequestApproval를 호출하는 함수.
    """
    steps = [
        approval_pb2.Step(
            step=step["step"],
            approverId=step["approverId"],
            status=step["status"],
        )
        for step in doc["steps"]
    ]

    request = approval_pb2.ApprovalRequest(
        requestId=doc["requestId"],
        requesterId=doc["requesterId"],
        title=doc["title"],
        content=doc["content"],
        steps=steps,
    )

    logger.info(
        "Sending RequestApproval via gRPC: target=%s, requestId=%s",
        APPROVAL_PROCESSING_GRPC_TARGET,
        doc["requestId"],
    )

    async with grpc.aio.insecure_channel(APPROVAL_PROCESSING_GRPC_TARGET) as channel:
        stub = approval_pb2_grpc.ApprovalStub(channel)
        response = await stub.RequestApproval(request)
        logger.info(
            "Received Response from RequestApproval: requestId=%s, message=%s",
            response.requestId,
            response.message,
        )
