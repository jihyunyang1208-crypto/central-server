# central-backend/app/models/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "AutoTrader", ".env")
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("WARNING: DATABASE_URL not set. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///./central_backend.db"

print(f"[Central Backend] DB URL: {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션 의존성 주입
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """모든 테이블 생성"""
    # 모든 모델 import (테이블 생성을 위해)
    from . import user, commission, kiwoom, trading_settings
    Base.metadata.create_all(bind=engine)
