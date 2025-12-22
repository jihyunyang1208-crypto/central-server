# central-backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..models.user import User
from ..models.commission import Referral, ReferralStatus
from ..schemas.user import UserResponse
from ..core.security import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자 정보 조회
    - 추천 코드 포함
    """
    return current_user


@router.get("/referral-stats")
def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    추천 통계 조회
    - 총 추천 수
    - 활성 추천 수 (ACTIVE 상태)
    """
    # 총 추천 수
    total_referrals = db.query(func.count(Referral.id)).filter(
        Referral.referrer_id == current_user.id
    ).scalar() or 0
    
    # 활성 추천 수 (ACTIVE 상태)
    active_referrals = db.query(func.count(Referral.id)).filter(
        Referral.referrer_id == current_user.id,
        Referral.status == ReferralStatus.ACTIVE
    ).scalar() or 0
    
    return {
        "total_referrals": total_referrals,
        "active_referrals": active_referrals
    }


@router.get("/me/referral-link")
def get_referral_link(
    current_user: User = Depends(get_current_user)
):
    """
    현재 사용자의 추천 링크 정보 조회
    """
    if not current_user.referral_code:
        raise HTTPException(status_code=404, detail="Referral code not found")
    
    # 추천 링크 생성 (프론트엔드 URL + ref 파라미터)
    base_url = "http://localhost:19006"  # TODO: 환경변수로 관리
    referral_url = f"{base_url}?ref={current_user.referral_code}"
    
    return {
        "referral_code": current_user.referral_code,
        "referral_url": referral_url
    }
