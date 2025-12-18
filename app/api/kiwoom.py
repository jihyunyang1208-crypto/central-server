# central-backend/app/api/kiwoom.py
"""
Kiwoom 브로커 인증 정보 관리 API
- 사용자별 AppKey/Secret 저장/조회
- 암호화 적용
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.database import get_db
from ..models.user import User
from ..models.kiwoom import KiwoomCredential
from ..schemas.kiwoom import (
    KiwoomCredentialCreate,
    KiwoomCredentialUpdate,
    KiwoomCredentialResponse,
    KiwoomCredentialDecrypted
)
from ..core.security import get_current_user
from ..core.crypto import encrypt_credential, decrypt_credential


router = APIRouter(prefix="/api/v1/kiwoom", tags=["Kiwoom"])


@router.post("/credentials", response_model=KiwoomCredentialResponse, status_code=status.HTTP_201_CREATED)
def create_kiwoom_credential(
    credential_data: KiwoomCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kiwoom 계좌 인증 정보 생성
    - AppKey/Secret 암호화 저장
    - 메인 계좌 설정 시 기존 메인 해제
    """
    # 중복 확인
    existing = db.query(KiwoomCredential).filter(
        KiwoomCredential.user_id == current_user.id,
        KiwoomCredential.account_id == credential_data.account_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account {credential_data.account_id} already exists"
        )
    
    # 메인 계좌 설정 시 기존 메인 해제
    if credential_data.is_main:
        db.query(KiwoomCredential).filter(
            KiwoomCredential.user_id == current_user.id,
            KiwoomCredential.is_main == True
        ).update({"is_main": False})
    
    # 암호화
    encrypted_app_key = encrypt_credential(credential_data.app_key)
    encrypted_secret_key = encrypt_credential(credential_data.secret_key)
    
    # 생성
    new_credential = KiwoomCredential(
        user_id=current_user.id,
        account_id=credential_data.account_id,
        alias=credential_data.alias,
        app_key=encrypted_app_key,
        secret_key=encrypted_secret_key,
        is_main=credential_data.is_main
    )
    
    db.add(new_credential)
    db.commit()
    db.refresh(new_credential)
    
    return new_credential


@router.get("/credentials", response_model=List[KiwoomCredentialResponse])
def list_kiwoom_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자의 모든 Kiwoom 계좌 목록 조회
    - 암호화된 상태로 반환 (보안)
    """
    credentials = db.query(KiwoomCredential).filter(
        KiwoomCredential.user_id == current_user.id
    ).all()
    
    return credentials


@router.get("/credentials/decrypted", response_model=List[KiwoomCredentialDecrypted])
def get_decrypted_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    복호화된 Kiwoom 인증 정보 조회
    - 로컬 트레이딩 서버에서 사용
    - 활성화된 계좌만 반환
    """
    credentials = db.query(KiwoomCredential).filter(
        KiwoomCredential.user_id == current_user.id,
        KiwoomCredential.is_active == True
    ).all()
    
    # 복호화
    decrypted_list = []
    for cred in credentials:
        decrypted_list.append(KiwoomCredentialDecrypted(
            id=cred.id,
            account_id=cred.account_id,
            alias=cred.alias,
            app_key=decrypt_credential(cred.app_key),
            secret_key=decrypt_credential(cred.secret_key),
            is_main=cred.is_main,
            is_active=cred.is_active
        ))
    
    return decrypted_list


@router.get("/credentials/{credential_id}", response_model=KiwoomCredentialResponse)
def get_kiwoom_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """특정 Kiwoom 계좌 정보 조회"""
    credential = db.query(KiwoomCredential).filter(
        KiwoomCredential.id == credential_id,
        KiwoomCredential.user_id == current_user.id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    return credential


@router.put("/credentials/{credential_id}", response_model=KiwoomCredentialResponse)
def update_kiwoom_credential(
    credential_id: int,
    update_data: KiwoomCredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Kiwoom 계좌 정보 업데이트
    - AppKey/Secret 변경 시 재암호화
    """
    credential = db.query(KiwoomCredential).filter(
        KiwoomCredential.id == credential_id,
        KiwoomCredential.user_id == current_user.id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    # 메인 계좌 변경 시 기존 메인 해제
    if update_data.is_main and not credential.is_main:
        db.query(KiwoomCredential).filter(
            KiwoomCredential.user_id == current_user.id,
            KiwoomCredential.is_main == True
        ).update({"is_main": False})
    
    # 업데이트
    if update_data.alias is not None:
        credential.alias = update_data.alias
    
    if update_data.app_key is not None:
        credential.app_key = encrypt_credential(update_data.app_key)
    
    if update_data.secret_key is not None:
        credential.secret_key = encrypt_credential(update_data.secret_key)
    
    if update_data.is_main is not None:
        credential.is_main = update_data.is_main
    
    if update_data.is_active is not None:
        credential.is_active = update_data.is_active
    
    db.commit()
    db.refresh(credential)
    
    return credential


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kiwoom_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kiwoom 계좌 정보 삭제"""
    credential = db.query(KiwoomCredential).filter(
        KiwoomCredential.id == credential_id,
        KiwoomCredential.user_id == current_user.id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    db.delete(credential)
    db.commit()
    
    return None
