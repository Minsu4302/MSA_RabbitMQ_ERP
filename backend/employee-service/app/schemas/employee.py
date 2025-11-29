from datetime import datetime
from pydantic import BaseModel, Field


class EmployeeBase(BaseModel):
    name: str = Field(..., max_length=100)
    department: str = Field(..., max_length=100)
    position: str = Field(..., max_length=100)


class EmployeeCreate(EmployeeBase):
    """POST /employees 요청 바디"""
    pass


class EmployeeUpdate(BaseModel):
    """PUT /employees/{id} 요청 바디

    name, created_at 같은 필드가 들어오면 에러가 나야 함.
    """
    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)

    class Config:
        extra = "forbid"  # 정의되지 않은 필드가 들어오면 422 에러


class Employee(EmployeeBase):
    """응답용 스키마"""
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
