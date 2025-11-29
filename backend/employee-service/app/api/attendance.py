from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee as EmployeeModel
from app.schemas.attendance import AttendanceCheckIn, AttendanceCheckOut, AttendanceRecordRead

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
)


@router.post(
    "/check-in",
    response_model=AttendanceRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def check_in(
    payload: AttendanceCheckIn,
    db: AsyncSession = Depends(get_db),
):
    """
    출근 처리:
    - 오늘(attendance_date 기준)에 이미 check_out 되지 않은 레코드가 있으면 400
    - 없으면 새 attendance_records 레코드 생성
    """
    now = datetime.utcnow()
    today = now.date()

    # 먼저 직원이 존재하는지 확인
    emp_stmt = select(EmployeeModel).where(EmployeeModel.id == payload.employee_id)
    emp_res = await db.execute(emp_stmt)
    emp_obj = emp_res.scalar_one_or_none()
    if emp_obj is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee not found")

    stmt = (
        select(AttendanceRecord)
        .where(
            and_(
                AttendanceRecord.employee_id == payload.employee_id,
                AttendanceRecord.attendance_date == today,
                AttendanceRecord.check_out.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in today",
        )

    record = AttendanceRecord(
        employee_id=payload.employee_id,
        attendance_date=today,
        check_in=now,
        check_out=None,
        work_minutes=None,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return AttendanceRecordRead.model_validate(record)


@router.post(
    "/check-out",
    response_model=AttendanceRecordRead,
)
async def check_out(
    payload: AttendanceCheckOut,
    db: AsyncSession = Depends(get_db),
):
    """
    퇴근 처리:
    - 오늘 출근 기록 중 check_out이 아직 없는 레코드를 찾아서
      check_out 시간 세팅 + work_minutes 계산
    """
    now = datetime.utcnow()
    today = now.date()

    stmt = (
        select(AttendanceRecord)
        .where(
            and_(
                AttendanceRecord.employee_id == payload.employee_id,
                AttendanceRecord.attendance_date == today,
                AttendanceRecord.check_out.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active attendance record for today",
        )

    record.check_out = now
    delta = now - record.check_in
    record.work_minutes = int(delta.total_seconds() // 60)

    await db.commit()
    await db.refresh(record)

    return AttendanceRecordRead.model_validate(record)


@router.get(
    "/me",
    response_model=List[AttendanceRecordRead],
)
async def get_my_attendance(
    employee_id: int = Query(..., alias="employeeId"),  # Query에서 요구하는 필드만 받기
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """
    특정 직원의 기간별 근태 기록 조회:
    GET /attendance/me?employeeId=1&from=2025-11-27&to=2025-11-30
    """
    stmt = (
        select(AttendanceRecord)
        .where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.attendance_date >= from_date,
                AttendanceRecord.attendance_date <= to_date,
            )
        )
        .order_by(AttendanceRecord.attendance_date)
    )

    result = await db.execute(stmt)
    records = result.scalars().all()

    return [AttendanceRecordRead.model_validate(r) for r in records]
