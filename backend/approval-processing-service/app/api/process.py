import os
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, status

from app.core.queue import WorkItem, approval_queue
from app.schemas.process import ProcessAction, WorkItemOut

router = APIRouter(
    prefix="/process",
    tags=["process"],
)

APPROVAL_REQUEST_BASE_URL = os.getenv(
    "APPROVAL_REQUEST_BASE_URL",
    "http://approval-request-service:8000",
)


async def _send_result_to_request_service(item: WorkItem) -> None:
    """
    Approval Request Service로 결재 결과를 REST로 전달.
    """
    payload = {
        "requestId": item.request_id,
        "step": item.step,
        "approverId": item.approver_id,
        "status": item.status,  # "approved" / "rejected"
    }

    async with httpx.AsyncClient(
        base_url=APPROVAL_REQUEST_BASE_URL,
        timeout=5.0,
    ) as client:
        resp = await client.post("/approvals/internal/result", json=payload)
        if resp.status_code >= 400:
            # 여기서 예외를 터뜨려도 되고, 로그만 남기고 넘겨도 됨
            # 수업용이라면 로그 & 예외 둘 다 남겨도 좋음
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to update approval result: {resp.status_code} {resp.text}",
            )


@router.get(
    "/{approver_id}",
    response_model=List[WorkItemOut],
)
async def list_pending(
    approver_id: int,
):
    items = approval_queue.list_items(approver_id)
    return [
        WorkItemOut(
            requestId=i.request_id,
            step=i.step,
            requesterId=i.requester_id,
            approverId=i.approver_id,
            title=i.title,
            content=i.content,
            status=i.status,
        )
        for i in items
    ]


@router.post(
    "/{approver_id}/{request_id}",
    response_model=WorkItemOut,
)
async def process_item(
    approver_id: int,
    request_id: int,
    action: ProcessAction,
):
    """
    결재자가 approve / reject 처리.
    1) In-Memory 큐에서 WorkItem 제거 + 상태 변경
    2) Approval Request Service에 결재 결과 REST 콜백
    """
    item = approval_queue.pop_item(approver_id, request_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending work item for this approver/requestId",
        )

    item.status = "approved" if action.action == "approve" else "rejected"

    # Approval Request Service에 결과 전달
    await _send_result_to_request_service(item)

    return WorkItemOut(
        requestId=item.request_id,
        step=item.step,
        requesterId=item.requester_id,
        approverId=item.approver_id,
        title=item.title,
        content=item.content,
        status=item.status,
    )
