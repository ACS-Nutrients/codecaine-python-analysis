import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.db.database import engine
from sqlalchemy import text

app = FastAPI(title="Analysis Service API", version="1.0.0")

# ECS 환경에서는 ALLOWED_ORIGINS 환경변수로 도메인 주입
# 미설정 시 로컬 개발용 기본값 사용
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    """ECS 헬스체크 전용 엔드포인트 — DB 연결 포함 확인"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "healthy", "db": "ok"})
    except Exception as e:
        return JSONResponse(
            content={"status": "unhealthy", "db": str(e)},
            status_code=503,
        )


@app.get("/")
def root():
    return {"message": "Analysis Service API", "status": "running"}
