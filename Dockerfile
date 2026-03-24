FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 이것만 추가
RUN pip install --no-cache-dir opentelemetry-distro opentelemetry-exporter-otlp
RUN opentelemetry-bootstrap -a install

COPY . .

EXPOSE 8000

# CMD만 앞에 opentelemetry-instrument 추가
CMD ["opentelemetry-instrument", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info", "--timeout-graceful-shutdown", "30"]