from datetime import datetime, date

from sqlalchemy import Column, BigInteger, Date, DateTime, Integer, String, ForeignKey

from app.core.db import Base


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)
    leave_type = Column(String(20), nullable=False)   # "annual", "sick", ...
    status = Column(String(20), nullable=False)       # "approved"
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
