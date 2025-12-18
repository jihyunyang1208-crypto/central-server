# central-backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """중앙 백엔드 서버 설정"""
    
    # 앱 정보
    APP_NAME: str = "AUT Central Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 데이터베이스
    DATABASE_URL: str
    
    # JWT 설정
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 암호화 키 (브로커 인증 정보 암호화용)
    MASTER_ENCRYPTION_KEY: str
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8082"]
    
    # 서버
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 커미션 설정
    COMMISSION_HOLDBACK_DAYS: int = 30
    
    # 결제 웹훅 (추후 설정)
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    TOSS_WEBHOOK_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"  # 현재 디렉토리의 .env 파일 사용
        case_sensitive = True
        extra = "ignore"  # 추가 필드 무시 (AutoTrader .env와 호환)


settings = Settings()
