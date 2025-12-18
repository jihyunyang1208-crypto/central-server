# central-backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
import string

from ..models.database import get_db
from ..models.user import User
from ..models.commission import Referral, ReferralStatus
from ..schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from ..core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    get_current_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def generate_referral_code(length: int = 8) -> str:
    """고유한 추천 코드 생성"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    회원가입
    - 이메일 중복 확인
    - 비밀번호 해싱 (argon2)
    - 추천 코드 생성
    - 추천인 연결 (referral_code 제공 시)
    """
    # 이메일 중복 확인
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 추천인 확인 (제공된 경우)
    referrer = None
    if user_data.referral_code:
        referrer = db.query(User).filter(User.referral_code == user_data.referral_code).first()
        if not referrer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid referral code"
            )
    
    # 고유한 추천 코드 생성
    while True:
        new_referral_code = generate_referral_code()
        if not db.query(User).filter(User.referral_code == new_referral_code).first():
            break
    
    # 사용자 생성
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        referral_code=new_referral_code,
        referred_by_id=referrer.id if referrer else None,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 추천 관계 생성 (추천인이 있는 경우)
    if referrer:
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=new_user.id,
            status=ReferralStatus.PENDING,
        )
        db.add(referral)
        db.commit()
    
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    로그인
    - 이메일/비밀번호 검증
    - JWT Access Token 및 Refresh Token 발급
    - 마지막 로그인 시간 업데이트
    """
    # 사용자 조회
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # [NEW] 구독 상태 확인
    from ..models.user import Subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription found"
        )
    
    # 구독 만료 확인
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription expired"
        )
    
    # 마지막 로그인 시간 업데이트
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # [NEW] AutoTrader에 START_TRADING 명령 전송
    import httpx
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        autotrader_url = os.getenv("AUTOTRADER_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{autotrader_url}/api/v1/trading/start",
                json={"user_token": access_token},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                logger.info(f"✅ START_TRADING sent to AutoTrader for user {user.id}")
            else:
                logger.warning(f"⚠️ START_TRADING failed: {response.status_code}")
                
    except Exception as e:
        # Don't fail login if START_TRADING fails
        logger.error(f"❌ Failed to send START_TRADING: {e}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """
    Refresh Token을 사용하여 새로운 Access Token 발급
    """
    from ..core.security import decode_token
    
    payload = decode_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # 새 토큰 발급
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/verify")
def verify_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    토큰 검증 및 구독 상태 반환
    AutoTrader가 START_TRADING 전에 호출하여 인증 확인
    """
    from ..models.user import Subscription
    
    # 구독 정보 조회
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    # 구독 활성 상태 확인
    subscription_active = False
    expires_at = None
    
    if subscription and subscription.expires_at:
        subscription_active = subscription.expires_at > datetime.utcnow()
        expires_at = subscription.expires_at.isoformat()
    
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "subscription_active": subscription_active,
        "expires_at": expires_at,
        "plan_type": subscription.plan.name if subscription and subscription.plan else None
    }
