from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AttendanceCheckIn(BaseModel):
    employee_id: int


class AttendanceCheckOut(BaseModel):
    employee_id: int


class AttendanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    attendance_date: date
    check_in: datetime
    check_out: Optional[datetime] = None
    work_minutes: Optional[int] = None
