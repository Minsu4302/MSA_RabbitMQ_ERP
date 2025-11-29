from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional


@dataclass
class WorkItem:
    request_id: int
    step: int
    requester_id: int
    approver_id: int
    title: str
    content: str
    status: str = "pending"


class ApprovalQueue:
    """
    approverId별로 처리 대기 중인 WorkItem을 보관하는 In-Memory 큐.
    """

    def __init__(self) -> None:
        # key: approverId, value: deque of WorkItem
        self._queues: Dict[int, Deque[WorkItem]] = defaultdict(deque)

    def enqueue(self, item: WorkItem) -> None:
        self._queues[item.approver_id].append(item)

    def list_items(self, approver_id: int) -> List[WorkItem]:
        return list(self._queues.get(approver_id, []))

    def pop_item(self, approver_id: int, request_id: int) -> Optional[WorkItem]:
        """
        해당 approver의 큐에서 request_id에 해당하는 WorkItem을 찾아 제거 후 반환.
        """
        q = self._queues.get(approver_id)
        if not q:
            return None

        for idx, item in enumerate(q):
            if item.request_id == request_id:
                # deque에서 제거
                del q[idx]
                if not q:
                    # 큐가 비면 key도 제거
                    del self._queues[approver_id]
                return item
        return None


# 전역 인스턴스 (REST와 gRPC가 함께 사용)
approval_queue = ApprovalQueue()
