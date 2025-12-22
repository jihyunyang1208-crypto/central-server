# central-backend/app/api/commissions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..core.database import get_db
from ..models.user import User
from ..models.commission import Commission, CommissionStatus, Referral
from ..schemas.commission import CommissionResponse, CommissionStatsResponse
from ..core.security import get_current_user

router = APIRouter(prefix="/api/v1/commissions", tags=["Commissions"])


@router.get("/me", response_model=List[CommissionResponse])
def get_my_commissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 커미션 내역 조회"""
    commissions = db.query(Commission).filter(
        Commission.user_id == current_user.id
    ).order_by(Commission.created_at.desc()).all()
    
    return commissions


@router.get("/stats", response_model=CommissionStatsResponse)
def get_commission_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """커미션 통계 조회"""
    # 상태별 합계
    stats = db.query(
        Commission.status,
        func.sum(Commission.amount).label("total")
    ).filter(
        Commission.user_id == current_user.id
    ).group_by(Commission.status).all()
    
    stats_dict = {stat.status: float(stat.total or 0) for stat in stats}
    
    # 추천 통계
    total_referrals = db.query(Referral).filter(
        Referral.referrer_id == current_user.id
    ).count()
    
    active_referrals = db.query(Referral).filter(
        Referral.referrer_id == current_user.id,
        Referral.status == "ACTIVE"
    ).count()
    
    return {
        "total_pending": stats_dict.get(CommissionStatus.PENDING, 0),
        "total_holdback": stats_dict.get(CommissionStatus.HOLDBACK, 0),
        "total_approved": stats_dict.get(CommissionStatus.APPROVED, 0),
        "total_paid": stats_dict.get(CommissionStatus.PAID, 0),
        "total_referrals": total_referrals,
        "active_referrals": active_referrals,
    }


@router.post("/request-payout")
def request_payout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    지급 요청
    - APPROVED 상태의 커미션만 지급 가능
    """
    approved_commissions = db.query(Commission).filter(
        Commission.user_id == current_user.id,
        Commission.status == CommissionStatus.APPROVED
    ).all()
    
    if not approved_commissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approved commissions available for payout"
        )
    
    total_amount = sum(c.amount for c in approved_commissions)
    
    # TODO: 실제 지급 처리 (은행 송금 등)
    # 여기서는 상태만 변경
    for commission in approved_commissions:
        commission.status = CommissionStatus.PAID
        commission.paid_at = func.now()
    
    db.commit()
    
    return {
        "message": "Payout request processed",
        "total_amount": total_amount,
        "currency": "KRW",
        "count": len(approved_commissions)
    }
