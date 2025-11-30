import os
from datetime import datetime, date
from typing import List
from pymongo import ReturnDocument

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.db import get_approvals_collection
from app.core.rabbitmq import publish_approval
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDocument,
    ApprovalResultUpdate,
    StepMessage,
    ApprovalWorkMessage,
)

router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
)

EMPLOYEE_SERVICE_BASE_URL = os.getenv(
    "EMPLOYEE_SERVICE_BASE_URL",
    "http://employee-service:8000",
)

NOTIFICATION_SERVICE_BASE_URL = os.getenv(
    "NOTIFICATION_SERVICE_BASE_URL",
    "http://notification-service:8000",
)


async def _send_notification(
    employee_id: int,
    payload: dict,
) -> None:
    """
    Notification Service에 REST로 알림 전달.
    """
    async with httpx.AsyncClient(
        base_url=NOTIFICATION_SERVICE_BASE_URL,
        timeout=5.0,
    ) as client:
        # 실패해도 서비스 전체가 죽지 않게 try/except로 감싸도 됨
        await client.post("/notify", json={"employeeId": employee_id, **payload})


async def _validate_employees(payload: ApprovalCreate) -> None:
    """
    Employee Service REST 호출로 requesterId / approverId 존재 여부 검증.
    - 존재하지 않는 직원 ID가 하나라도 있으면 400 에러.
    """
    ids = {payload.requesterId} | {step.approverId for step in payload.steps}

    async with httpx.AsyncClient(
        base_url=EMPLOYEE_SERVICE_BASE_URL,
        timeout=5.0,
    ) as client:
        for employee_id in ids:
            resp = await client.get(f"/employees/{employee_id}")
            if resp.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee {employee_id} not found in Employee Service",
                )
            if resp.status_code != status.HTTP_200_OK:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        f"Employee Service error for id {employee_id} "
                        f"(status={resp.status_code})"
                    ),
                )


async def _get_next_request_id(
    collection: AsyncIOMotorCollection,
) -> int:
    """Atomic하게 requestId 증가.
    counters 컬렉션에 {_id: 'approval_request_id', seq: N} 형태로 저장 후 $inc.
    동시성 레이스 조건 제거.
    """
    counter = await collection.database["counters"].find_one_and_update(
        {"_id": "approval_request_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(counter["seq"])


def _serialize_document(raw: dict) -> ApprovalDocument:
    """
    MongoDB Document(dict) -> Pydantic 모델로 변환.
    _id 필드는 응답에서 제외.
    """
    data = raw.copy()
    data.pop("_id", None)
    return ApprovalDocument(**data)


async def _confirm_leave_if_needed(doc: dict) -> None:
    """
    연차 타입(LEAVE)의 결재가 최종 승인된 경우,
    Employee Service의 내부 연차 확정 API를 호출한다.
    """
    if doc.get("requestType") != "LEAVE":
        return
    if doc.get("finalStatus") != "approved":
        return

    leave = doc.get("leaveInfo")
    if not leave:
        return

    payload = {
        "employeeId": doc["requesterId"],
        "startDate": leave["startDate"],
        "endDate": leave["endDate"],
        "days": leave["days"],
        "leaveType": leave.get("leaveType", "annual"),
        "reason": leave.get("reason"),
        "requestId": doc["requestId"],
    }
    payload = jsonable_encoder(payload)

    async with httpx.AsyncClient(
        base_url=EMPLOYEE_SERVICE_BASE_URL,
        timeout=5.0,
    ) as client:
        await client.post("/leaves/internal/approved", json=payload)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_approval(
    payload: ApprovalCreate,
    request: Request,
    collection: AsyncIOMotorCollection = Depends(get_approvals_collection),
):
    """
    결재 요청 생성
    흐름:
    1) Employee Service로 requester/approver 존재 검증
    2) requestId 발급
    3) MongoDB에 Document 저장 (finalStatus/steps.status 초기값 pending)
    4) RabbitMQ로 Approval Processing Service에 Work 메시지 publish
    """
    # 0. 연차 타입일 때 leaveInfo 필수 검증
    if payload.requestType == "LEAVE" and payload.leaveInfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="leaveInfo is required when requestType is LEAVE",
        )

    # 1. 직원 존재 검증
    await _validate_employees(payload)

    # 2. requestId 생성
    request_id = await _get_next_request_id(collection)
    now = datetime.utcnow()

    steps_doc = [
        {
            "step": step.step,
            "approverId": step.approverId,
            "status": "pending",
            "updatedAt": None,
        }
        for step in payload.steps
    ]

    # serialize and normalize leaveInfo so MongoDB/PyMongo can encode it
    leave_info = None
    if payload.leaveInfo is not None:
        leave_info = jsonable_encoder(payload.leaveInfo)

        def _normalize_dates(obj):
            if isinstance(obj, dict):
                return {k: _normalize_dates(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_normalize_dates(v) for v in obj]
            # convert date (but not datetime) to ISO string
            if isinstance(obj, date) and not isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        leave_info = _normalize_dates(leave_info)

    doc = {
        "requestId": request_id,
        "requesterId": payload.requesterId,
        "title": payload.title,
        "content": payload.content,
        "steps": steps_doc,
        "finalStatus": "pending",
        "requestType": payload.requestType,
        "leaveInfo": leave_info,
        "createdAt": now,
        "updatedAt": now,
    }

    # 3. MongoDB 저장
    await collection.insert_one(doc)

    # 4. RabbitMQ로 첫 번째 WorkItem 전달
    work_message = ApprovalWorkMessage(
        requestId=doc["requestId"],
        requesterId=doc["requesterId"],
        title=doc["title"],
        content=doc["content"],
        steps=[
            StepMessage(
                step=s["step"],
                approverId=s["approverId"],
                status=s["status"],
            )
            for s in doc["steps"]
        ],
    )
    await publish_approval(request.app, work_message)

    # Response: {"requestId": 1}
    return {"requestId": request_id}


@router.get(
    "",
    response_model=List[ApprovalDocument],
)
async def list_approvals(
    collection: AsyncIOMotorCollection = Depends(get_approvals_collection),
):
    """
    모든 결재 요청 목록 조회
    """
    cursor = collection.find({})
    docs = await cursor.to_list(length=1000)
    return [_serialize_document(doc) for doc in docs]


@router.get(
    "/{request_id}",
    response_model=ApprovalDocument,
)
async def get_approval(
    request_id: int,
    collection: AsyncIOMotorCollection = Depends(get_approvals_collection),
):
    """
    특정 requestId에 해당하는 결재 요청 상세 조회
    """
    doc = await collection.find_one({"requestId": request_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    return _serialize_document(doc)


@router.post(
    "/internal/result",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_approval_result(
    payload: ApprovalResultUpdate,
    request: Request,
    collection: AsyncIOMotorCollection = Depends(get_approvals_collection),
):
    """
    Approval Processing Service에서 호출하는 내부용 API.

    1) requestId로 Document 조회
    2) 해당 step + approverId 매칭되는 step 상태 변경 + updatedAt 갱신
    3) finalStatus 재계산
    4) finalStatus가 in_progress이면 다음 step을 위해 RabbitMQ로 메시지 재전송
    5) requesterId / approverId에게 Notification Service 통해 알림
    6) LEAVE 타입이면서 최종 approved인 경우 Employee Service에 연차 확정 요청
    """
    doc = await collection.find_one({"requestId": payload.requestId})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    steps = doc.get("steps", [])
    target_step = None
    for step in steps:
        if (
            step.get("step") == payload.step
            and step.get("approverId") == payload.approverId
        ):
            target_step = step
            break

    if target_step is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matching approval step not found",
        )

    # step 상태/시간 갱신
    target_step["status"] = payload.status
    target_step["updatedAt"] = datetime.utcnow()

    # finalStatus 재계산
    statuses = [s.get("status") for s in steps]
    if "rejected" in statuses:
        final_status = "rejected"
    elif all(s == "approved" for s in statuses):
        final_status = "approved"
    elif any(s == "approved" for s in statuses):
        final_status = "in_progress"
    else:
        final_status = "pending"

    doc["steps"] = steps
    doc["finalStatus"] = final_status
    doc["updatedAt"] = datetime.utcnow()

    await collection.replace_one({"_id": doc["_id"]}, doc)

    # 다음 step이 남아 있는 경우(= in_progress) → RabbitMQ로 다음 WorkItem 전달
    if final_status == "in_progress":
        work_message = ApprovalWorkMessage(
            requestId=doc["requestId"],
            requesterId=doc["requesterId"],
            title=doc["title"],
            content=doc["content"],
            steps=[
                StepMessage(
                    step=s["step"],
                    approverId=s["approverId"],
                    status=s["status"],
                )
                for s in doc["steps"]
            ],
        )
        await publish_approval(request.app, work_message)

    # 최종 approved + LEAVE 타입이면 Employee Service에 연차 확정 요청
    if final_status == "approved":
        await _confirm_leave_if_needed(doc)

    # Notification Service로 알림 전송 (요청자 + 결재자)
    notify_payload = {
        "type": "approval_result",
        "requestId": doc["requestId"],
        "step": payload.step,
        "approverId": payload.approverId,
        "finalStatus": final_status,
        "stepStatus": payload.status,
        "title": doc["title"],
    }

    # 요청자에게 알림
    await _send_notification(doc["requesterId"], notify_payload)
    # 해당 결재자에게도 알림
    await _send_notification(payload.approverId, notify_payload)

    # 204 No Content
