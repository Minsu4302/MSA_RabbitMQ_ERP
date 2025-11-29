from datetime import datetime, date

from sqlalchemy import Column, BigInteger, Date, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.core.db import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime, nullable=True)
    work_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 선택: Employee 모델에 relationship 정의해둔 경우 사용 가능
    # employee = relationship("Employee", back_populates="attendance_records")
