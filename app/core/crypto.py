# central-backend/app/core/crypto.py
"""
암호화/복호화 유틸리티
- Fernet 대칭 암호화 사용
- MASTER_ENCRYPTION_KEY 기반
"""
from cryptography.fernet import Fernet
from .config import settings


# Fernet 암호화 인스턴스
cipher = Fernet(settings.MASTER_ENCRYPTION_KEY.encode())


def encrypt_credential(data: str) -> str:
    """
    인증 정보 암호화
    
    Args:
        data: 평문 데이터
    
    Returns:
        암호화된 문자열
    """
    return cipher.encrypt(data.encode()).decode()


def decrypt_credential(encrypted: str) -> str:
    """
    인증 정보 복호화
    
    Args:
        encrypted: 암호화된 데이터
    
    Returns:
        복호화된 평문
    """
    return cipher.decrypt(encrypted.encode()).decode()
