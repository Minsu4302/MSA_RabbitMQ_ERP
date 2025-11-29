from datetime import datetime, date
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator


class StepCreate(BaseModel):
    step: int = Field(..., ge=1)
    approverId: int = Field(..., ge=1)


class StepInDocument(BaseModel):
    step: int
    approverId: int
    status: str
    updatedAt: Optional[datetime] = None


class LeaveInfo(BaseModel):
    """
    연차 신청 정보 (LEAVE 타입인 결재에서만 사용).
    """
    startDate: date
    endDate: date
    days: int
    leaveType: str = "annual"
    reason: Optional[str] = None


class ApprovalCreate(BaseModel):
    """
    POST /approvals 요청 바디
    """
    requesterId: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    steps: List[StepCreate]

    # 창의 기능 확장: 일반 결재 vs 연차 결재 구분
    requestType: Literal["GENERAL", "LEAVE"] = "GENERAL"
    leaveInfo: Optional[LeaveInfo] = None

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: List[StepCreate]) -> List[StepCreate]:
        """
        가이드 요구사항:
        - steps가 1부터 오름차순인지 검증.
        """
        if not v:
            raise ValueError("steps must not be empty")

        sorted_steps = sorted(v, key=lambda s: s.step)
        for i, step in enumerate(sorted_steps, start=1):
            if step.step != i:
                raise ValueError(
                    "steps must start at 1 and be consecutive in ascending order"
                )
        return v


class ApprovalDocument(BaseModel):
    """
    MongoDB에 저장된 결재 요청 Document 응답용
    """
    requestId: int
    requesterId: int
    title: str
    content: str
    steps: List[StepInDocument]
    finalStatus: str
    createdAt: datetime
    updatedAt: datetime

    # 확장 필드
    requestType: Literal["GENERAL", "LEAVE"] = "GENERAL"
    leaveInfo: Optional[LeaveInfo] = None


class ApprovalResultUpdate(BaseModel):
    requestId: int
    step: int
    approverId: int
    status: Literal["approved", "rejected"]


class StepMessage(BaseModel):
    step: int
    approverId: int
    status: str  # "pending" | "approved" | "rejected"


class ApprovalWorkMessage(BaseModel):
    requestId: int
    requesterId: int
    title: str
    content: str
    steps: List[StepMessage]
