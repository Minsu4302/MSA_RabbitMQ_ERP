from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.leave import LeaveRecord

router = APIRouter(
    prefix="/leaves",
    tags=["leaves"],
)


class LeaveApprovedPayload(BaseModel):
    """
    Approval Request Service에서 최종 승인된 연차 정보를 넘겨줄 때 사용하는 내부용 스키마.
    """
    employeeId: int
    startDate: date
    endDate: date
    days: int
    leaveType: str = "annual"
    reason: Optional[str] = None
    requestId: Optional[int] = None  # trace 용, DB에는 저장 안 해도 됨


class LeaveRecordRead(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    days: int
    leave_type: str
    status: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post(
    "/internal/approved",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def create_approved_leave(
    payload: LeaveApprovedPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Approval Request Service에서 최종 승인된 연차를 기록하는 내부용 API.

    - status는 항상 "approved"로 저장
    - 나중에 필요하면 requestId를 별도 테이블이나 audit 로그에 남기는 것도 가능
    """
    record = LeaveRecord(
        employee_id=payload.employeeId,
        start_date=payload.startDate,
        end_date=payload.endDate,
        days=payload.days,
        leave_type=payload.leaveType,
        status="approved",
        reason=payload.reason,
    )
    db.add(record)
    await db.commit()
    # 204 No Content, 바디 없음
    return


@router.get(
    "/me",
    response_model=List[LeaveRecordRead],
)
async def get_my_leaves(
    employee_id: int = Query(..., alias="employeeId"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """
    특정 직원의 연차 사용 내역 조회.

    예:
    GET /leaves/me?employeeId=1
    GET /leaves/me?employeeId=1&from=2025-12-01&to=2025-12-31
    """
    stmt = select(LeaveRecord).where(LeaveRecord.employee_id == employee_id)

    if from_date is not None:
        stmt = stmt.where(LeaveRecord.start_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(LeaveRecord.end_date <= to_date)

    stmt = stmt.order_by(LeaveRecord.start_date)

    result = await db.execute(stmt)
    records = result.scalars().all()

    return [LeaveRecordRead.model_validate(r) for r in records]
