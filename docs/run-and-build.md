# 빌드 및 실행 가이드

## 1. 사전 요구사항

### 1.1 필수 설치 항목

- **Docker Desktop**: 컨테이너 이미지 빌드 및 실행
- **Kubernetes**: Docker Desktop 내장 Kubernetes 또는 별도 클러스터
- **kubectl**: Kubernetes 클라이언트 CLI
- **Python 3.12+**: 로컬 개발 시 필요 (선택)
- **Git**: 소스 코드 관리

### 1.2 환경 확인

```powershell
# Docker 버전 확인
docker --version

# Kubernetes 클러스터 연결 확인
kubectl cluster-info

# 네임스페이스 확인
kubectl get namespaces
```

## 2. Docker 이미지 빌드

### 2.1 전체 서비스 빌드

프로젝트 루트 디렉토리에서 다음 명령어를 순서대로 실행합니다.

```powershell
# Employee Service
docker build -t gkdltpa1/infra-employee-service:latest .\backend\employee-service

# Approval Request Service
docker build -t gkdltpa1/infra-approval-request-service:latest .\backend\approval-request-service

# Approval Processing Service
docker build -t gkdltpa1/infra-approval-processing-service:latest .\backend\approval-processing-service

# Notification Service
docker build -t gkdltpa1/infra-notification-service:latest .\backend\notification-service
```

### 2.2 개별 서비스 빌드 (캐시 없이)

문제 해결이나 코드 변경 후 완전히 새로 빌드할 때 사용합니다.

```powershell
docker build --no-cache -t gkdltpa1/infra-employee-service:latest .\backend\employee-service
```

### 2.3 이미지 확인

```powershell
# 빌드된 이미지 목록 확인
docker images | Select-String "infra-"
```

**예상 출력**:
```
gkdltpa1/infra-employee-service              latest    abc123def456   5 minutes ago   200MB
gkdltpa1/infra-approval-request-service      latest    def789ghi012   4 minutes ago   195MB
gkdltpa1/infra-approval-processing-service   latest    ghi345jkl678   3 minutes ago   195MB
gkdltpa1/infra-notification-service          latest    jkl901mno234   2 minutes ago   190MB
```

## 3. Docker Registry에 푸시 (선택)

원격 Kubernetes 클러스터나 팀원과 이미지 공유 시 필요합니다.

### 3.1 Docker Hub 로그인

```powershell
docker login
```

### 3.2 이미지 푸시

```powershell
docker push gkdltpa1/infra-employee-service:latest
docker push gkdltpa1/infra-approval-request-service:latest
docker push gkdltpa1/infra-approval-processing-service:latest
docker push gkdltpa1/infra-notification-service:latest
```

> ℹ️ **참고**: 로컬 Docker Desktop Kubernetes를 사용하는 경우 푸시 단계를 건너뛸 수 있습니다.
> Deployment YAML에서 `imagePullPolicy: IfNotPresent`로 설정하면 로컬 이미지를 우선 사용합니다.

## 4. Kubernetes 배포

### 4.1 네임스페이스 생성

```powershell
kubectl apply -f k8s\namespace.yaml
```

**확인**:
```powershell
kubectl get namespace erp
```

### 4.2 데이터베이스 및 메시지 브로커 배포

```powershell
# MySQL 배포
kubectl apply -f k8s\mysql\deployment.yaml
kubectl apply -f k8s\mysql\service.yaml

# MongoDB 배포
kubectl apply -f k8s\mongodb\deployment.yaml
kubectl apply -f k8s\mongodb\service.yaml

# RabbitMQ 배포
kubectl apply -f k8s\rabbitmq\deployment.yaml
kubectl apply -f k8s\rabbitmq\service.yaml
```

**확인**:
```powershell
kubectl get pods -n erp
```

**예상 출력**:
```
NAME                          READY   STATUS    RESTARTS   AGE
mysql-xxxxxxxxxx-xxxxx        1/1     Running   0          1m
mongodb-xxxxxxxxxx-xxxxx      1/1     Running   0          1m
rabbitmq-xxxxxxxxxx-xxxxx     1/1     Running   0          1m
```

> ⏱️ **대기 시간**: 모든 Pod가 Running 상태가 될 때까지 1-2분 정도 소요됩니다.

### 4.3 애플리케이션 서비스 배포

데이터베이스가 준비된 후 순서대로 배포합니다.

```powershell
# Employee Service
kubectl apply -f k8s\employee-service\deployment.yaml
kubectl apply -f k8s\employee-service\service.yaml

# Approval Request Service
kubectl apply -f k8s\approval-request-service\deployment.yaml
kubectl apply -f k8s\approval-request-service\service.yaml

# Approval Processing Service
kubectl apply -f k8s\approval-processing-service\deployment.yaml
kubectl apply -f k8s\approval-processing-service\service.yaml

# Notification Service
kubectl apply -f k8s\notification-service\deployment.yaml
kubectl apply -f k8s\notification-service\service.yaml
```

### 4.4 전체 리소스 확인

```powershell
# Pod 상태 확인
kubectl get pods -n erp

# Service 확인
kubectl get svc -n erp

# Deployment 확인
kubectl get deployments -n erp
```

**예상 출력 (전체)**:
```
NAME                                  READY   STATUS    RESTARTS   AGE
employee-service-xxxxxxxxxx-xxxxx     1/1     Running   0          2m
approval-request-service-xxx-xxxxx   1/1     Running   0          2m
approval-processing-service-xx-xxx   1/1     Running   0          2m
notification-service-xxxxxxx-xxxxx   1/1     Running   0          2m
mysql-xxxxxxxxxx-xxxxx                1/1     Running   0          3m
mongodb-xxxxxxxxxx-xxxxx              1/1     Running   0          3m
rabbitmq-xxxxxxxxxx-xxxxx             1/1     Running   0          3m
```

## 5. 이미지 업데이트 및 재배포

코드 변경 후 새 이미지를 배포하는 방법입니다.

### 5.1 이미지 재빌드 및 푸시

```powershell
# 예: Approval Request Service 수정 후
docker build --no-cache -t gkdltpa1/infra-approval-request-service:latest .\backend\approval-request-service
docker push gkdltpa1/infra-approval-request-service:latest
```

### 5.2 Kubernetes 배포 업데이트

**방법 1: set image 명령어 사용**
```powershell
kubectl set image deployment/approval-request-service `
  approval-request-service=gkdltpa1/infra-approval-request-service:latest `
  -n erp
```

**방법 2: rollout restart (로컬 이미지 사용 시)**
```powershell
kubectl rollout restart deployment/approval-request-service -n erp
```

### 5.3 롤아웃 상태 확인

```powershell
# 롤아웃 완료 대기
kubectl rollout status deployment/approval-request-service -n erp

# Pod 재시작 확인
kubectl get pods -n erp -w
```

## 6. 포트 포워딩 설정

로컬에서 서비스에 접근하기 위해 포트 포워딩을 설정합니다.

### 6.1 각 서비스 포트 포워딩

**터미널 1: Employee Service**
```powershell
kubectl port-forward -n erp svc/employee-service 8001:8000
```

**터미널 2: Approval Request Service**
```powershell
kubectl port-forward -n erp svc/approval-request-service 8002:8000
```

**터미널 3: Approval Processing Service**
```powershell
kubectl port-forward -n erp svc/approval-processing-service 8003:8000
```

**터미널 4: Notification Service**
```powershell
kubectl port-forward -n erp svc/notification-service 8004:8000
```

> ⚠️ **주의**: 각 포트 포워딩은 별도 터미널에서 실행해야 하며, 터미널을 종료하면 포워딩도 종료됩니다.

### 6.2 접근 URL 확인

포트 포워딩 완료 후 다음 URL로 접근 가능합니다:

- **Employee Service API**: http://localhost:8001/docs
- **Approval Request Service API**: http://localhost:8002/docs
- **Approval Processing Service API**: http://localhost:8003/docs
- **Notification Service API**: http://localhost:8004/docs
- **WebSocket**: ws://localhost:8004/ws/{employeeId}

### 6.3 빠른 헬스 체크

```powershell
# 모든 서비스 헬스 체크 (포트 포워딩 후)
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

## 7. 로그 확인

### 7.1 실시간 로그 보기

```powershell
# Pod 이름 확인
$pod = (kubectl get pods -n erp | Select-String approval-request-service | Select-Object -First 1).ToString().Split()[0]

# 실시간 로그 출력
kubectl logs -f -n erp $pod
```

### 7.2 최근 로그 확인

```powershell
# 최근 100줄 로그
kubectl logs -n erp $pod --tail=100

# 최근 5분간 로그
kubectl logs -n erp $pod --since=5m
```

### 7.3 모든 서비스 로그 한 번에 보기

```powershell
# Employee Service
kubectl logs -n erp -l app=employee-service --tail=50

# Approval Request Service
kubectl logs -n erp -l app=approval-request-service --tail=50

# Approval Processing Service
kubectl logs -n erp -l app=approval-processing-service --tail=50

# Notification Service
kubectl logs -n erp -l app=notification-service --tail=50
```

## 8. 데이터베이스 초기화

### 8.1 MySQL 초기 스키마

Employee Service는 시작 시 자동으로 테이블을 생성합니다 (`app/core/db.py`의 `init_db()` 함수).

수동 초기화가 필요한 경우:

```powershell
# MySQL Pod에 접속
$mysqlPod = (kubectl get pods -n erp | Select-String mysql | Select-Object -First 1).ToString().Split()[0]
kubectl exec -it -n erp $mysqlPod -- mysql -u root -prootpassword erp

# SQL 실행
mysql> SHOW TABLES;
mysql> SELECT * FROM employees;
mysql> EXIT;
```

### 8.2 MongoDB 확인

```powershell
# MongoDB Pod에 접속
$mongoPod = (kubectl get pods -n erp | Select-String mongodb | Select-Object -First 1).ToString().Split()[0]
kubectl exec -it -n erp $mongoPod -- mongosh erp

# 컬렉션 확인
db.approvals.find().pretty();
exit
```

## 9. 환경 변수 설정

### 9.1 서비스별 환경 변수

각 서비스의 Deployment YAML에서 환경 변수를 설정할 수 있습니다.

**예: `k8s/employee-service/deployment.yaml`**
```yaml
env:
  - name: MYSQL_HOST
    value: "mysql"
  - name: MYSQL_PORT
    value: "3306"
  - name: MYSQL_USER
    value: "root"
  - name: MYSQL_PASSWORD
    value: "rootpassword"
  - name: MYSQL_DATABASE
    value: "erp"
```

### 9.2 ConfigMap 사용 (권장)

민감하지 않은 설정은 ConfigMap으로 관리합니다.

**configmap.yaml 생성**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: erp
data:
  MYSQL_HOST: "mysql"
  MYSQL_PORT: "3306"
  MYSQL_DATABASE: "erp"
  MONGODB_URI: "mongodb://mongodb:27017"
  RABBITMQ_HOST: "rabbitmq"
```

**적용**:
```powershell
kubectl apply -f k8s\configmap.yaml
```

**Deployment에서 참조**:
```yaml
envFrom:
  - configMapRef:
      name: app-config
```

### 9.3 Secret 사용 (비밀번호 등)

민감한 정보는 Secret으로 관리합니다.

```powershell
kubectl create secret generic db-credentials `
  --from-literal=MYSQL_PASSWORD=rootpassword `
  --from-literal=MONGODB_PASSWORD=mongopassword `
  -n erp
```

**Deployment에서 참조**:
```yaml
env:
  - name: MYSQL_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: MYSQL_PASSWORD
```

## 10. 트러블슈팅

### 10.1 Pod가 시작되지 않는 경우

```powershell
# Pod 상태 확인
kubectl describe pod <pod-name> -n erp

# 로그 확인
kubectl logs <pod-name> -n erp

# 이벤트 확인
kubectl get events -n erp --sort-by='.lastTimestamp'
```

**일반적인 문제**:
- `ImagePullBackOff`: 이미지 이름/태그 확인 또는 `imagePullPolicy: IfNotPresent` 설정
- `CrashLoopBackOff`: 로그에서 애플리케이션 에러 확인
- `Pending`: 리소스 부족 또는 PVC 문제

### 10.2 서비스 연결 안 됨

```powershell
# Service 엔드포인트 확인
kubectl get endpoints -n erp

# DNS 테스트 (Pod 내부에서)
kubectl exec -it <pod-name> -n erp -- nslookup mysql
```

### 10.3 데이터베이스 연결 실패

```powershell
# MySQL Pod 상태 확인
kubectl logs <mysql-pod> -n erp

# 연결 테스트
kubectl exec -it <mysql-pod> -n erp -- mysql -u root -prootpassword -e "SHOW DATABASES;"
```

### 10.4 이미지 업데이트 반영 안 됨

```powershell
# Pod 강제 재시작
kubectl delete pod <pod-name> -n erp

# 또는 전체 Deployment 재시작
kubectl rollout restart deployment/<deployment-name> -n erp

# 이미지 pull 강제
kubectl set image deployment/<deployment-name> <container-name>=<image>:latest -n erp
kubectl rollout restart deployment/<deployment-name> -n erp
```

## 11. 전체 재배포 (클린 스타트)

모든 리소스를 삭제하고 처음부터 다시 시작하는 방법입니다.

```powershell
# 1. 네임스페이스 전체 삭제 (모든 리소스 포함)
kubectl delete namespace erp

# 2. 네임스페이스 재생성
kubectl apply -f k8s\namespace.yaml

# 3. 위의 "4. Kubernetes 배포" 섹션을 처음부터 다시 수행
```

## 12. 성능 모니터링

### 12.1 리소스 사용량 확인

```powershell
# Pod별 CPU/메모리 사용량
kubectl top pods -n erp

# Node 리소스 사용량
kubectl top nodes
```

### 12.2 HPA (Horizontal Pod Autoscaler) 설정 (선택)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: employee-service-hpa
  namespace: erp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: employee-service
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

```powershell
kubectl apply -f k8s\hpa.yaml
kubectl get hpa -n erp
```

## 13. 빠른 시작 스크립트

전체 빌드 및 배포를 한 번에 수행하는 스크립트입니다.

**`scripts/deploy-all.ps1`**:
```powershell
# 이미지 빌드
Write-Host "Building Docker images..." -ForegroundColor Green
docker build -t gkdltpa1/infra-employee-service:latest .\backend\employee-service
docker build -t gkdltpa1/infra-approval-request-service:latest .\backend\approval-request-service
docker build -t gkdltpa1/infra-approval-processing-service:latest .\backend\approval-processing-service
docker build -t gkdltpa1/infra-notification-service:latest .\backend\notification-service

# Kubernetes 배포
Write-Host "Deploying to Kubernetes..." -ForegroundColor Green
kubectl apply -f k8s\namespace.yaml
kubectl apply -f k8s\mysql\
kubectl apply -f k8s\mongodb\
kubectl apply -f k8s\rabbitmq\
Start-Sleep -Seconds 10
kubectl apply -f k8s\employee-service\
kubectl apply -f k8s\approval-request-service\
kubectl apply -f k8s\approval-processing-service\
kubectl apply -f k8s\notification-service\

Write-Host "Deployment complete! Waiting for pods..." -ForegroundColor Green
kubectl wait --for=condition=ready pod -l app=employee-service -n erp --timeout=120s

Write-Host "All services deployed successfully!" -ForegroundColor Green
kubectl get pods -n erp
```

**실행**:
```powershell
.\scripts\deploy-all.ps1
```

## 14. 다음 단계

배포가 완료되면:

1. **API 테스트**: `docs/api-design.md` 참조하여 각 엔드포인트 테스트
2. **시나리오 테스트**: 결재 승인, 근태 기록, 연차 신청 등 전체 플로우 검증
3. **WebSocket 테스트**: 브라우저 또는 wscat으로 실시간 알림 확인
4. **문제 해결**: 에러 발생 시 `docs/troubleshooting.md` 참조
