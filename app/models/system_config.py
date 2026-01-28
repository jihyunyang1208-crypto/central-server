# app/models/system_config.py
"""
시스템 설정 모델
- Gemini AI 모델 우선순위
- Gemini API 키
- 기타 시스템 전역 설정
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class SystemConfig(Base):
    """시스템 설정 테이블"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String, unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)  # 업데이트한 관리자 이메일
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemConfig(key={self.config_key})>"
