from sqlalchemy import BigInteger, Column, DateTime, String, func

from app.core.db import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
