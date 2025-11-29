FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 👇 소스 코드 복사 (중요!)
COPY app /app/app

EXPOSE 8000

# K8s에서는 --reload 빼도 되지만, 있어도 치명적이진 않음
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
