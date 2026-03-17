from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

_engine = None
_SessionLocal = None

def get_engine():
    """engine을 처음 호출 시점에 생성 (lazy init). 모듈 임포트 시 DB 연결 시도 방지."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.get_database_url(),
            pool_pre_ping=True,   # 끊긴 연결 자동 감지 (ECS 재시작·RDS 재연결 대비)
            pool_recycle=1800,    # 30분마다 연결 재생성 (RDS idle timeout 대비)
            pool_size=5,
            max_overflow=10,
        )
    return _engine

def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

def get_db():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
