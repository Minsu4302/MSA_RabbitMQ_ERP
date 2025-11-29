from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.employee import Employee as EmployeeModel
from app.schemas.employee import (
    Employee as EmployeeSchema,
    EmployeeCreate,
    EmployeeUpdate,
)

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
):
    employee = EmployeeModel(
        name=payload.name,
        department=payload.department,
        position=payload.position,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)

    # 가이드: {"id": 10} 형태로 응답
    return {"id": employee.id}


@router.get(
    "",
    response_model=List[EmployeeSchema],
)
async def list_employees(
    department: str | None = None,
    position: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(EmployeeModel)

    if department:
        stmt = stmt.where(EmployeeModel.department == department)
    if position:
        stmt = stmt.where(EmployeeModel.position == position)

    result = await db.execute(stmt)
    employees = result.scalars().all()
    return employees


@router.get(
    "/{employee_id}",
    response_model=EmployeeSchema,
)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


@router.put(
    "/{employee_id}",
    response_model=EmployeeSchema,
)
async def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    # 둘 다 None이면 업데이트할 게 없음 → 에러
    if payload.department is None and payload.position is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'department' or 'position' must be provided",
        )

    if payload.department is not None:
        employee.department = payload.department
    if payload.position is not None:
        employee.position = payload.position

    await db.commit()
    await db.refresh(employee)

    return employee


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmployeeModel).where(EmployeeModel.id == employee_id)
    )
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    await db.delete(employee)
    await db.commit()
    # 204 No Content → 바디 없음
