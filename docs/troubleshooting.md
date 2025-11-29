# 문제 해결 가이드 (Troubleshooting)

본 문서는 개발 과정에서 발생한 문제와 해결 방법을 정리한 것입니다.

## 목차

1. [데이터베이스 연결 문제](#1-데이터베이스-연결-문제)
2. [Import 및 의존성 문제](#2-import-및-의존성-문제)
3. [gRPC 관련 문제](#3-grpc-관련-문제)
4. [Kubernetes 배포 문제](#4-kubernetes-배포-문제)
5. [FastAPI 의존성 문제](#5-fastapi-의존성-문제)
6. [MongoDB 데이터 직렬화 문제](#6-mongodb-데이터-직렬화-문제)
7. [서비스 간 통신 문제](#7-서비스-간-통신-문제)
8. [기타 문제](#8-기타-문제)

---

## 1. 데이터베이스 연결 문제

### 1.1 MySQL async 드라이버 + 인증 오류

**문제**:
```
RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password auth methods
```

**원인**:
- MySQL 8의 기본 인증 방식인 `caching_sha2_password`를 `asyncmy` 드라이버가 처리하려면 `cryptography` 패키지가 필요
- `requirements.txt`에 해당 패키지가 누락됨

**해결**:

1. `backend/employee-service/requirements.txt`에 추가:
```txt
cryptography
```

2. 이미지 재빌드:
```powershell
docker build --no-cache -t gkdltpa1/infra-employee-service:latest .\backend\employee-service
```

**교훈**:
- DB 드라이버 에러는 대부분 "드라이버 + 인증 방식 + 의존성 패키지 조합" 문제
- MySQL 8 사용 시 인증 플러그인과 드라이버 요구사항을 반드시 확인

---

### 1.2 K8s MySQL 새로 띄운 후 테이블 없음

**문제**:
```python
ProgrammingError: (1146, "Table 'erp.employees' doesn't exist")
```

**원인**:
- Kubernetes MySQL은 `emptyDir` 볼륨 사용 시 완전히 빈 DB로 시작
- 애플리케이션이 스키마 자동 생성 코드를 실행하지 않음

**해결**:

1. `app/core/db.py`에 `init_db()` 함수 추가:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.employee import Base  # 모든 모델의 Base import

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """데이터베이스 테이블 초기화"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

2. `app/main.py`의 startup 이벤트에서 호출:
```python
from app.core.db import init_db

@app.on_event("startup")
async def startup_event():
    await init_db()
    logger.info("Database initialized")
```

**교훈**:
- Kubernetes처럼 항상 새로 뜨는 환경에서는 DB 마이그레이션/스키마 초기화 전략 필수
- 간단한 과제에서는 `create_all()`로 해결 가능하지만, 실제 서비스에서는 Alembic 등 마이그레이션 도구 사용 권장

---

## 2. Import 및 의존성 문제

### 2.1 불필요한 SQLAlchemy import

**문제**:
```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**원인**:
- MongoDB만 사용하는 `approval-request-service`에 복사한 코드에서 SQLAlchemy import가 남아있음
- 실제로 사용하지 않는 라이브러리를 import하면 불필요한 의존성 발생

**해결**:

1. 불필요한 import 삭제:
```python
# 삭제
from sqlalchemy.exc import SQLAlchemyError

# 필요한 것만 유지
from motor.motor_asyncio import AsyncIOMotorClient
```

2. `requirements.txt`에서도 제거

**교훈**:
- 복사/붙여넣기 후 사용하지 않는 import는 반드시 정리
- 서비스의 책임과 사용 라이브러리를 최소화하는 것이 좋음

---

### 2.2 Pydantic v2에서 BaseSettings 이동

**문제**:
```
ImportError: BaseSettings has been moved to the 'pydantic-settings' package
```

**원인**:
- Pydantic v2에서 `BaseSettings`가 별도 패키지로 분리됨
- 기존 코드에서 `from pydantic import BaseSettings` 사용 중

**해결**:

1. `requirements.txt`에 추가:
```txt
pydantic-settings
```

2. import 수정:
```python
# Before
from pydantic import BaseSettings

# After
from pydantic_settings import BaseSettings
```

3. `app/core/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    # ...

    class Config:
        env_file = ".env"

settings = Settings()
```

**교훈**:
- 메이저 버전 업그레이드(v1 → v2) 시 breaking changes 확인 필수
- 환경 변수 관리는 이제 `pydantic-settings` 사용 권장

---

## 3. gRPC 관련 문제

### 3.1 gRPC stub import 경로 문제

**문제**:
```
ModuleNotFoundError: No module named 'approval_pb2'
```

**원인**:
- `grpc_tools.protoc`로 생성된 stub 파일 내부에서 `import approval_pb2`로 절대 import 사용
- 패키지 구조와 PYTHONPATH가 맞지 않음

**해결**:

1. stub 파일을 `app/grpc_stubs/` 안에 배치
2. 서비스 코드에서 상대 경로로 import:
```python
from app.grpc_stubs import approval_pb2, approval_pb2_grpc
```

3. 필요 시 generated 코드의 import를 수정:
```python
# approval_pb2_grpc.py 내부
import app.grpc_stubs.approval_pb2 as approval__pb2
```

**교훈**:
- gRPC stub 생성 시 패키지 구조를 미리 설계
- proto 파일 컴파일 시 `--python_out`과 `--grpc_python_out` 경로를 명확히 지정

---

### 3.2 protobuf runtime 에러

**문제**:
```
ModuleNotFoundError: No module named 'google'
```

**원인**:
- `protobuf`, `grpcio`, `grpcio-tools` 패키지가 설치되지 않음

**해결**:

`requirements.txt`에 추가:
```txt
grpcio>=1.50.0
protobuf>=4.21.0
grpcio-tools>=1.50.0
```

**교훈**:
- gRPC 사용 시 컴파일러와 runtime 라이브러리 세트로 설치 필요

---

### 3.3 gRPC 서버 시작 안 함

**문제**:
- gRPC 서버 로그(`Starting gRPC server on ...`)가 찍히지 않음
- FastAPI는 정상 동작하지만 gRPC만 시작되지 않음

**원인**:
- `uvicorn --reload`와 gRPC 서버를 별도 스레드로 실행하는 구조에서 reloader 프로세스와 충돌

**해결**:

1. FastAPI `startup` 이벤트에서 gRPC 서버를 백그라운드로 안전하게 실행:
```python
import asyncio
from concurrent import futures

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    executor = futures.ThreadPoolExecutor(max_workers=10)
    
    def serve_grpc():
        server = grpc.server(executor)
        approval_pb2_grpc.add_ApprovalServicer_to_server(ApprovalService(), server)
        server.add_insecure_port('[::]:50051')
        server.start()
        server.wait_for_termination()
    
    loop.run_in_executor(None, serve_grpc)
```

2. 또는 RabbitMQ로 전환하여 gRPC 의존성 제거 (4.2 심화 과제에서 채택)

**교훈**:
- FastAPI + gRPC 동시 사용 시 reloader와 스레드/loop 관리에 주의
- 심화 과제에서는 메시지 브로커가 더 단순하고 확장성 있는 대안

---

## 4. Kubernetes 배포 문제

### 4.1 이미지 Pull 실패 (ErrImagePull)

**문제**:
```
ErrImagePull
ImagePullBackOff
pull access denied for your-docker-id/...
```

**원인**:
- 예시로 쓰던 이미지 이름을 그대로 사용
- 로컬 이미지만 빌드하고 `imagePullPolicy: Always`로 설정해 Docker Hub에서만 찾으려 함

**해결**:

**방법 1**: 로컬 이미지 사용 (Docker Desktop Kubernetes)
```yaml
spec:
  containers:
  - name: employee-service
    image: gkdltpa1/infra-employee-service:latest
    imagePullPolicy: IfNotPresent  # 로컬 우선
```

**방법 2**: Docker Hub에 푸시 후 사용
```powershell
docker push gkdltpa1/infra-employee-service:latest
```

**교훈**:
- K8s에서 사용할 실제 이미지 이름과 `imagePullPolicy`를 환경에 맞게 설정
- 로컬 클러스터에서는 로컬 이미지 재사용이 편리

---

### 4.2 Docker 컨테이너 내 코드 미복사

**문제**:
```
Error loading ASGI app. Could not import module "app.main"
connection refused
```

**원인**:
- Dockerfile에서 `RUN mkdir -p /app/app`만 하고 실제 소스 코드를 `COPY`하지 않음

**해결**:

각 서비스 Dockerfile 수정:
```dockerfile
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 이 줄 추가!
COPY app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

이미지 재빌드:
```powershell
docker build --no-cache -t gkdltpa1/infra-employee-service:latest .\backend\employee-service
kubectl rollout restart deployment/employee-service -n erp
```

**교훈**:
- 컨테이너 안에서 실제 파일 구조를 한 번 확인하는 것이 중요
- ASGI 앱 import 실패는 소스 미복사/경로 오류일 때 자주 발생

---

### 4.3 Ingress ADDRESS 없음

**문제**:
```powershell
kubectl get ingress -n erp
# ADDRESS 컬럼이 비어있음
```
```
http://erp.local → Connection Refused
```

**원인**:
- Ingress 리소스 YAML은 작성했지만, 실제 Ingress Controller(nginx ingress 등)를 클러스터에 설치하지 않음

**해결**:

**방법 1**: Ingress Controller 설치 (프로덕션)
```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

**방법 2**: 과제 범위에서는 포트 포워딩 사용 (권장)
```powershell
kubectl port-forward -n erp svc/employee-service 8001:8000
```

**교훈**:
- Ingress 리소스만으로는 동작하지 않고, Controller가 반드시 필요
- 실습 환경에서는 포트 포워딩이 더 단순

---

## 5. FastAPI 의존성 문제

### 5.1 FastAPI Depends + sessionmaker → local_kw 버그

**문제**:
```json
{
  "detail": [
    {
      "loc": ["query", "local_kw"],
      "msg": "Field required"
    }
  ]
}
```
- Swagger UI에서 `local_kw`라는 알 수 없는 쿼리 파라미터가 나타남

**원인**:
- `Depends(AsyncSessionLocal)`로 sessionmaker를 직접 FastAPI 의존성에 주입
- FastAPI가 이 callable의 시그니처를 분석하면서 내부 `**local_kw` 인자를 보고 OpenAPI 스펙에 쿼리 파라미터로 노출

**해결**:

`get_db()` 의존성 함수를 직접 구현:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

API에서 사용:
```python
@router.post("/attendance/check-in")
async def check_in(
    payload: AttendanceCheckIn,
    db: AsyncSession = Depends(get_db)  # sessionmaker 대신 get_db
):
    # ...
```

**교훈**:
- FastAPI 의존성에 직접 sessionmaker를 넣는 것보다 `get_db()` 패턴이 안전
- 422 + 이상한 query param이 보이면 OpenAPI 스펙 / Depends 설정을 의심

---

## 6. MongoDB 데이터 직렬화 문제

### 6.1 연차 결재 생성 시 500 에러 (datetime.date 직렬화)

**문제**:
```
POST /approvals (requestType: "LEAVE" + leaveInfo)
→ 500 Internal Server Error
```

**Pod 로그**:
```python
bson.errors.InvalidDocument: Invalid document {...} | 
cannot encode object: datetime.date(2025, 12, 1), of type: <class 'datetime.date'>
```

**원인**:
1. MongoDB(PyMongo)는 Python의 `datetime.date` 객체를 직접 인코딩할 수 없음
2. `leaveInfo.startDate`, `endDate`가 Pydantic에서 `date` 타입으로 파싱되어 그대로 Document에 삽입
3. `datetime`만 import하고 `datetime.date`를 사용하려다 TypeError 발생

**해결**:

1. import 수정:
```python
from datetime import datetime, date
from fastapi.encoders import jsonable_encoder
```

2. `create_approval`에서 `leaveInfo` 직렬화 로직 추가:
```python
# serialize and normalize leaveInfo so MongoDB/PyMongo can encode it
leave_info = None
if payload.leaveInfo is not None:
    leave_info = jsonable_encoder(payload.leaveInfo)

    def _normalize_dates(obj):
        if isinstance(obj, dict):
            return {k: _normalize_dates(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_normalize_dates(v) for v in obj]
        # convert date (but not datetime) to ISO string
        if isinstance(obj, date) and not isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    leave_info = _normalize_dates(leave_info)

doc = {
    # ...
    "leaveInfo": leave_info,
    # ...
}
```

**배포 및 검증**:
```powershell
docker build --no-cache -t gkdltpa1/infra-approval-request-service:latest .\backend\approval-request-service
docker push gkdltpa1/infra-approval-request-service:latest
kubectl rollout restart deployment/approval-request-service -n erp
```

테스트:
```powershell
curl -X POST http://localhost:8002/approvals `
  -H "Content-Type: application/json" `
  -d '{
    "requesterId": 1,
    "title": "연차 신청 (12/1~12/2)",
    "content": "연말 여행",
    "steps": [{"step": 1, "approverId": 2}],
    "requestType": "LEAVE",
    "leaveInfo": {
      "startDate": "2025-12-01",
      "endDate": "2025-12-02",
      "days": 2,
      "leaveType": "annual",
      "reason": "연말 여행"
    }
  }'
```

**결과**:
- HTTP 201 Created
- 응답: `{"requestId": 4}`

**교훈**:
- MongoDB에 Python 객체 저장 시 bson이 인코딩할 수 있는 타입인지 확인 필수
- `jsonable_encoder` + 후처리 조합으로 안전하게 직렬화 가능
- `date` → ISO 문자열, `datetime` → 그대로 저장 (MongoDB native 지원)

---

## 7. 서비스 간 통신 문제

### 7.1 Approval Processing → Request 콜백 경로 mismatch

**문제**:
```
POST http://approval-request-service:8000/internal/approvals/result → 404
502 Bad Gateway
```

**원인**:
- Approval Request Service 라우터:
  ```python
  APIRouter(prefix="/approvals")
  @router.post("/internal/result")
  ```
  실제 경로: `/approvals/internal/result`
  
- Processing Service에서 잘못된 경로로 호출:
  ```python
  POST /internal/approvals/result
  ```

**해결**:

콜백 URL 수정:
```python
# approval-processing-service/app/api/process.py
async with httpx.AsyncClient(
    base_url=APPROVAL_REQUEST_BASE_URL,
    timeout=10.0
) as client:
    resp = await client.post(
        "/approvals/internal/result",  # 올바른 경로
        json=callback_data
    )
```

**교훈**:
- APIRouter의 `prefix`와 엔드포인트 상대 경로 조합을 함께 고려
- 내부 콜백 API는 URL 오타로 인한 404가 많이 발생하므로 주의

---

### 7.2 Employee Service 호출 시 502

**문제**:
```json
{
  "detail": "Employee Service error for id 1 (status=502)"
}
```

**원인**:
- Employee Service가 실행 중이지 않거나 헬스체크 실패
- 네트워크 정책 또는 DNS 문제

**해결**:

1. Employee Service Pod 상태 확인:
```powershell
kubectl get pods -n erp | Select-String employee-service
kubectl logs -n erp <employee-service-pod>
```

2. Service 엔드포인트 확인:
```powershell
kubectl get endpoints -n erp employee-service
```

3. DNS 테스트:
```powershell
kubectl exec -it <approval-request-pod> -n erp -- nslookup employee-service
```

4. 직접 curl 테스트:
```powershell
kubectl exec -it <approval-request-pod> -n erp -- curl http://employee-service:8000/health
```

**교훈**:
- 서비스 간 통신 문제는 Pod 상태 → Service → DNS 순으로 확인
- 502는 대상 서비스가 응답하지 않는다는 의미

---

## 8. 기타 문제

### 8.1 Approve API Method Not Allowed (405)

**문제**:
```json
{
  "detail": "Method Not Allowed"
}
```

**원인**:
- 라우터가 `@router.get`으로 선언되어 있거나 클라이언트가 잘못 GET으로 호출

**해결**:

1. 엔드포인트 메서드 확인:
```python
@router.post("/{approver_id}/{request_id}")  # POST 확인
async def process_approval(...):
    pass
```

2. 클라이언트 호출 확인:
```powershell
curl -X POST http://localhost:8003/process/2/1 \  # POST 명시
  -H "Content-Type: application/json" \
  -d '{"action":"approve"}'
```

**교훈**:
- "조회는 GET, 상태 변경은 POST/PUT/PATCH/DELETE" 기본 규칙 재확인
- Swagger로 실제 등록된 메서드 확인 습관화

---

### 8.2 Swagger "Failed to fetch"

**문제**:
- Swagger UI에서 API 호출 시 "Failed to fetch. Possible Reasons: CORS, Network Failure..."

**원인**:
- 실제로는 서버에서 `NameError: name 'Literal' is not defined` 발생
- 서버가 크래시되어 Swagger 입장에서는 네트워크 에러처럼 보임

**해결**:

1. 서버 로그 먼저 확인:
```powershell
kubectl logs -n erp <pod-name> --tail=100
```

2. 누락된 import 추가:
```python
from typing import Literal

class ApprovalResultUpdate(BaseModel):
    status: Literal["approved", "rejected"]
```

**교훈**:
- Swagger의 "Failed to fetch"는 꼭 CORS 문제가 아님
- 서버 로그를 먼저 확인해야 함

---

## 9. 문제 해결 체크리스트

문제 발생 시 다음 순서로 확인:

### 9.1 로컬 개발 환경
- [ ] Python 버전 확인 (3.12+)
- [ ] 가상환경 활성화 확인
- [ ] `requirements.txt` 모든 패키지 설치 확인
- [ ] 환경 변수 설정 확인 (`.env` 파일)
- [ ] 데이터베이스 실행 및 연결 확인

### 9.2 Docker 이미지
- [ ] Dockerfile에 `COPY app /app/app` 포함 확인
- [ ] 이미지 빌드 성공 확인
- [ ] 로컬에서 컨테이너 실행 테스트
- [ ] 포트 포워딩 확인

### 9.3 Kubernetes
- [ ] Pod 상태 확인 (`kubectl get pods`)
- [ ] Pod 로그 확인 (`kubectl logs`)
- [ ] Service 엔드포인트 확인
- [ ] 이미지 pull 정책 확인
- [ ] ConfigMap/Secret 확인
- [ ] 리소스 제한 확인

### 9.4 서비스 간 통신
- [ ] 대상 서비스 실행 확인
- [ ] DNS 해석 확인
- [ ] 엔드포인트 URL 정확성 확인
- [ ] HTTP 메서드 확인
- [ ] Request/Response 스키마 확인

### 9.5 데이터베이스
- [ ] DB Pod 실행 확인
- [ ] 연결 문자열 확인
- [ ] 인증 정보 확인
- [ ] 테이블/컬렉션 존재 확인
- [ ] 권한 확인

---

## 10. 추가 디버깅 팁

### 10.1 로그 레벨 조정

개발 시 더 자세한 로그를 보려면:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 10.2 SQLAlchemy 쿼리 로그

```python
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=True  # SQL 쿼리 출력
)
```

### 10.3 HTTP 클라이언트 로그

```python
import httpx
import logging

logging.getLogger("httpx").setLevel(logging.DEBUG)
```

### 10.4 Pod 내부 직접 테스트

```powershell
# Pod 쉘 접속
kubectl exec -it <pod-name> -n erp -- /bin/sh

# Python REPL 실행
python

# 직접 코드 테스트
>>> import asyncio
>>> from app.main import app
>>> # ...
```

---

**문제가 해결되지 않을 때**:
1. 에러 메시지 전체를 복사하여 검색
2. 관련 공식 문서 확인 (FastAPI, SQLAlchemy, Motor 등)
3. GitHub Issues에서 유사 문제 검색
4. 간단한 재현 케이스 작성하여 단계별 디버깅
