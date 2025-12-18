# central-backend/app/models/kiwoom.py
"""
Kiwoom 브로커 인증 정보 모델
- 사용자별 계좌 AppKey/Secret 관리
- 암호화 저장
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class KiwoomCredential(Base):
    """키움 브로커 API 인증 정보"""
    __tablename__ = "kiwoom_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    
    # 계좌 정보
    account_id = Column(String, index=True, nullable=False, comment="계좌번호")
    alias = Column(String, comment="계좌 별칭")
    
    # 암호화된 인증 정보
    app_key = Column(String, nullable=False, comment="암호화된 App Key")
    secret_key = Column(String, nullable=False, comment="암호화된 Secret Key")
    
    # 상태
    is_main = Column(Boolean, default=False, comment="메인 계좌 여부")
    is_active = Column(Boolean, default=True, comment="활성화 상태")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계
    user = relationship("User", backref="kiwoom_credentials")
