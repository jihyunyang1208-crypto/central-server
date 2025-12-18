# central-backend/app/schemas/kiwoom.py
"""
Kiwoom API 스키마
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class KiwoomCredentialCreate(BaseModel):
    """Kiwoom 인증 정보 생성"""
    account_id: str
    alias: Optional[str] = None
    app_key: str
    secret_key: str
    is_main: bool = False


class KiwoomCredentialUpdate(BaseModel):
    """Kiwoom 인증 정보 업데이트"""
    alias: Optional[str] = None
    app_key: Optional[str] = None
    secret_key: Optional[str] = None
    is_main: Optional[bool] = None
    is_active: Optional[bool] = None


class KiwoomCredentialResponse(BaseModel):
    """Kiwoom 인증 정보 응답 (암호화된 상태)"""
    id: int
    user_id: int
    account_id: str
    alias: Optional[str]
    is_main: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class KiwoomCredentialDecrypted(BaseModel):
    """복호화된 Kiwoom 인증 정보 (로컬 서버로 전송용)"""
    id: int
    account_id: str
    alias: Optional[str]
    app_key: str  # 복호화됨
    secret_key: str  # 복호화됨
    is_main: bool
    is_active: bool
