# central-backend/app/api/subscriptions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from ..core.database import get_db
from ..models.user import User, Subscription, SubscriptionStatus
from ..models.commission import SubscriptionPlan, Referral, ReferralStatus
from ..schemas.subscription import (
    SubscriptionPlanResponse,
    SubscriptionResponse,
    SubscriptionCreate,
    SubscriptionUpgrade,
)
from ..core.security import get_current_user
from ..services.commission_calculator import trigger_commission_event

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
def get_subscription_plans(db: Session = Depends(get_db)):
    """사용 가능한 구독 플랜 목록 조회"""
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    return plans


@router.get("/me", response_model=SubscriptionResponse)
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """내 구독 정보 조회"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    return subscription


@router.post("/subscribe", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def subscribe(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    구독 시작
    - 플랜 선택
    - 결제 처리 (실제 결제는 웹훅에서 처리)
    - 추천인에게 커미션 발생
    """
    # 기존 구독 확인
    existing_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if existing_subscription and existing_subscription.status == SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already have an active subscription"
        )
    
    # 플랜 확인
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == subscription_data.plan_id).first()
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # 구독 생성
    new_subscription = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.PENDING,  # 결제 완료 시 ACTIVE로 변경
        payment_method_id=subscription_data.payment_method_id,
        auto_renew=True,
    )
    
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)
    
    # TODO: 실제 결제 처리 (Stripe/Toss 등)
    # 여기서는 즉시 활성화 (테스트용)
    new_subscription.status = SubscriptionStatus.ACTIVE
    new_subscription.started_at = datetime.utcnow()
    new_subscription.expires_at = datetime.utcnow() + timedelta(days=30)  # 월 구독 가정
    new_subscription.last_payment_at = datetime.utcnow()
    db.commit()
    
    # 추천 관계 활성화 및 커미션 발생
    referral = db.query(Referral).filter(
        Referral.referred_id == current_user.id,
        Referral.status == ReferralStatus.PENDING
    ).first()
    
    if referral:
        referral.status = ReferralStatus.ACTIVE
        referral.activated_at = datetime.utcnow()
        db.commit()
        
        # 커미션 발생 (비동기 처리)
        trigger_commission_event(
            db=db,
            referral_id=referral.id,
            event_type="SIGNUP",
            subscription_amount=plan.price_monthly
        )
    
    return new_subscription


@router.put("/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    upgrade_data: SubscriptionUpgrade,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구독 플랜 변경 (업그레이드/다운그레이드)"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    new_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == upgrade_data.new_plan_id
    ).first()
    
    if not new_plan or not new_plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New plan not found"
        )
    
    # 플랜 변경
    subscription.plan_id = new_plan.id
    db.commit()
    db.refresh(subscription)
    
    # 업그레이드 시 커미션 발생
    referral = db.query(Referral).filter(
        Referral.referred_id == current_user.id,
        Referral.status == ReferralStatus.ACTIVE
    ).first()
    
    if referral:
        trigger_commission_event(
            db=db,
            referral_id=referral.id,
            event_type="UPGRADE",
            subscription_amount=new_plan.price_monthly
        )
    
    return subscription


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """구독 취소"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.cancelled_at = datetime.utcnow()
    subscription.auto_renew = False
    db.commit()
    
    # 추천 관계 만료
    referral = db.query(Referral).filter(
        Referral.referred_id == current_user.id,
        Referral.status == ReferralStatus.ACTIVE
    ).first()
    
    if referral:
        referral.status = ReferralStatus.EXPIRED
        db.commit()
    
    return {"message": "Subscription cancelled successfully"}


@router.get("/validate")
def validate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    구독 상태 검증 (로컬 트레이딩 서버용)
    - 만료일 확인
    - 플랜 제한 반환
    - 트레이딩 서버 활성화 여부 판단
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription found"
        )
    
    # 만료 확인
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        subscription.status = SubscriptionStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription expired"
        )
    
    # 플랜 정보 조회
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == subscription.plan_id
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription plan not found"
        )
    
    return {
        "valid": True,
        "plan_name": plan.name,  # Use plan.name (PRO/STANDARD/FREE) instead of display_name
        "max_conditions": plan.max_conditions,
        "max_stocks": plan.max_stocks,
        "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
    }
