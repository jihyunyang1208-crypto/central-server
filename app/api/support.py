from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.support import SupportInquiry
from app.schemas.support import SupportInquiryCreate, SupportInquiryResponse

router = APIRouter(prefix="/support", tags=["Support"])

@router.post("/inquiry", response_model=SupportInquiryResponse)
def create_inquiry(inquiry: SupportInquiryCreate, db: Session = Depends(get_db)):
    """새로운 지원 문의를 생성합니다."""
    db_inquiry = SupportInquiry(
        user_email=inquiry.user_email,
        title=inquiry.title,
        content=inquiry.content
    )
    db.add(db_inquiry)
    db.commit()
    db.refresh(db_inquiry)
    return db_inquiry

@router.get("/inquiries", response_model=List[SupportInquiryResponse])
def get_inquiries(db: Session = Depends(get_db)):
    """(관리자용) 모든 지원 문의를 조회합니다."""
    # TODO: 관리자 권한 체크 추가
    return db.query(SupportInquiry).order_by(SupportInquiry.created_at.desc()).all()
@router.get("/setup-info")
def get_setup_info():
    """AutoTrader 설치 및 설정 정보를 반환합니다."""
    return {
        "installer_url": "https://raw.githubusercontent.com/jihyunyang1208-crypto/AUT_v1/main/Setup/AutoTrader_Setup.exe",
        "latest_version": "1.0.0",
        "description": "High-End AutoTrader Installer"
    }
