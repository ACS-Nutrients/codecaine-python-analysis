FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# ECS는 SIGTERM으로 컨테이너를 종료하므로 uvicorn이 graceful shutdown 처리
# --timeout-graceful-shutdown: SIGTERM 수신 후 최대 30초 대기
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "--timeout-graceful-shutdown", "30"]
