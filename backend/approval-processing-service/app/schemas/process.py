from pydantic import BaseModel, Field


class WorkItemOut(BaseModel):
    requestId: int
    step: int
    requesterId: int
    approverId: int
    title: str
    content: str
    status: str

    class Config:
        from_attributes = True  # dataclass -> Pydantic 변환용


class ProcessAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
