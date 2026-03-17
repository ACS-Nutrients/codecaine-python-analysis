from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.get_database_url(),
    pool_pre_ping=True,       # 끊긴 연결 자동 감지 (ECS 재시작·RDS 재연결 대비)
    pool_recycle=1800,        # 30분마다 연결 재생성 (RDS idle timeout 대비)
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
