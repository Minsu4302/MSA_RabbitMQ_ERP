import logging

import grpc

from app.core.queue import WorkItem, approval_queue
from app.grpc_stubs import approval_pb2, approval_pb2_grpc

logger = logging.getLogger(__name__)


class ApprovalService(approval_pb2_grpc.ApprovalServicer):
    """
    Approval Request Service에서 들어오는 RequestApproval gRPC를 처리하는 서버.
    """

    async def RequestApproval(
        self,
        request: approval_pb2.ApprovalRequest,
        context: grpc.aio.ServicerContext,
    ) -> approval_pb2.ApprovalResponse:
        """
        ApprovalRequest 메시지를 받아서 각 approverId별 큐에 WorkItem으로 적재.
        """
        logger.info(
            "Received RequestApproval: requestId=%s, requesterId=%s, steps=%d",
            request.requestId,
            request.requesterId,
            len(request.steps),
        )

        for step in request.steps:
            item = WorkItem(
                request_id=request.requestId,
                step=step.step,
                requester_id=request.requesterId,
                approver_id=step.approverId,
                title=request.title,
                content=request.content,
            )
            approval_queue.enqueue(item)
            logger.info(
                "Enqueued WorkItem: requestId=%s, step=%s, approverId=%s",
                item.request_id,
                item.step,
                item.approver_id,
            )

        return approval_pb2.ApprovalResponse(
            requestId=request.requestId,
            message="Enqueued successfully",
        )
