# central-backend/app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class User(Base):
    """사용자 테이블 - 인증 및 기본 정보"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # 상태 관리
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False, comment="Admin dashboard access")
    
    # 추천 시스템
    referral_code = Column(String, unique=True, index=True, nullable=True, comment="내 추천 코드")
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="나를 추천한 사용자 ID")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True, index=True, comment="Last activity timestamp")
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referrals_received = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred")
    commissions = relationship("Commission", back_populates="user")


class SubscriptionStatus(str, enum.Enum):
    """구독 상태"""
    ACTIVE = "ACTIVE"           # 활성
    EXPIRED = "EXPIRED"         # 만료
    CANCELLED = "CANCELLED"     # 취소
    PENDING = "PENDING"         # 결제 대기


class Subscription(Base):
    """사용자 구독 정보"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # 구독 플랜 (외래키로 SubscriptionPlan 참조)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    
    # 상태
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING, index=True)
    
    # 기간
    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # 결제 정보
    auto_renew = Column(Boolean, default=True)
    payment_method_id = Column(String, nullable=True, comment="결제 수단 ID (Stripe/Toss 등)")
    billing_key = Column(String, nullable=True, index=True, comment="토스 빌링키 (자동결제용)")
    billing_period = Column(String, default='monthly', comment="결제 주기: monthly, yearly")
    card_last4 = Column(String(4), nullable=True, comment="카드 마지막 4자리")
    card_company = Column(String, nullable=True, comment="카드사")
    last_payment_at = Column(DateTime, nullable=True)
    next_payment_date = Column(DateTime, nullable=True, index=True, comment="다음 자동결제 예정일")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
