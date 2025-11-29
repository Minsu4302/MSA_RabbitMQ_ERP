from typing import List

from pydantic import BaseModel


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
