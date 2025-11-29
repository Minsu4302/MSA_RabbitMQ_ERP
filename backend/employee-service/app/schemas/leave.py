from datetime import date, datetime
from pydantic import BaseModel


class LeaveCreate(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    days: int
    leave_type: str = "annual"
    reason: str | None = None


class LeaveRecordRead(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    days: int
    leave_type: str
    status: str
    reason: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
