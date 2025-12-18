# central-backend/app/api/trading_settings.py
"""
트레이딩 설정 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..models.database import get_db
from ..models.user import User, Subscription
from ..models.trading_settings import TradingSettings
from ..models.commission import SubscriptionPlan
from ..schemas.trading_settings import (
    TradingSettingsResponse,
    TradingSettingsUpdate,
    TradingSettingsCreate
)
from ..core.security import get_current_user

router = APIRouter(prefix="/api/v1/settings", tags=["trading-settings"])


def get_user_plan_type(user_id: int, db: Session) -> str:
    """사용자 플랜 타입 조회"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    if not subscription or not subscription.plan:
        return "FREE"
    
    # SubscriptionPlan에 plan_type 필드가 있다고 가정
    # 없으면 plan name으로 판단
    if hasattr(subscription.plan, 'plan_type'):
        return subscription.plan.plan_type
    
    # Fallback: name으로 판단
    plan_name = subscription.plan.name.upper()
    if "PRO" in plan_name:
        return "PRO"
    elif "STANDARD" in plan_name or "BASIC" in plan_name:
        return "STANDARD"
    else:
        return "FREE"


@router.get("/trading", response_model=TradingSettingsResponse)
async def get_trading_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 트레이딩 설정 조회
    - 설정이 없으면 기본값으로 생성
    """
    settings = db.query(TradingSettings).filter(
        TradingSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # 기본 설정 생성
        settings = TradingSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.put("/trading", response_model=TradingSettingsResponse)
async def update_trading_settings(
    settings_update: TradingSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 트레이딩 설정 업데이트
    - Pro 기능 사용 시 플랜 검증
    """
    # 기존 설정 조회 또는 생성
    settings = db.query(TradingSettings).filter(
        TradingSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = TradingSettings(user_id=current_user.id)
        db.add(settings)
    
    # 플랜 검증
    user_plan = get_user_plan_type(current_user.id, db)
    
    # Pro 기능 사용 시 플랜 확인
    if settings_update.buy_mode == "PRO" and user_plan != "PRO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro buy features require Pro plan subscription"
        )
    
    if settings_update.sell_mode == "PRO" and user_plan != "PRO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro sell features require Pro plan subscription"
        )
    
    # 전략 개수 제한 검증
    if settings_update.max_active_strategies is not None:
        max_allowed = 5 if user_plan == "STANDARD" else 20 if user_plan == "PRO" else 3
        if settings_update.max_active_strategies > max_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your plan allows maximum {max_allowed} strategies"
            )
    
    # 업데이트 적용
    update_data = settings_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/trading", response_model=TradingSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_trading_settings(
    settings_create: TradingSettingsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    트레이딩 설정 생성 (명시적)
    - 일반적으로 GET 시 자동 생성되므로 선택적
    """
    # 기존 설정 확인
    existing = db.query(TradingSettings).filter(
        TradingSettings.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trading settings already exist. Use PUT to update."
        )
    
    # 플랜 검증
    user_plan = get_user_plan_type(current_user.id, db)
    
    if settings_create.buy_mode == "PRO" and user_plan != "PRO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro buy features require Pro plan subscription"
        )
    
    if settings_create.sell_mode == "PRO" and user_plan != "PRO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro sell features require Pro plan subscription"
        )
    
    # 생성
    settings = TradingSettings(
        user_id=current_user.id,
        **settings_create.dict()
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    
    return settings
