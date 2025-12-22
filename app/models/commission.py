# central-backend/app/models/commission.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum
from app.core.database import Base


class ReferralStatus(str, enum.Enum):
    """추천 상태"""
    PENDING = "PENDING"         # 대기 (가입만 완료)
    ACTIVE = "ACTIVE"           # 활성 (구독 시작)
    EXPIRED = "EXPIRED"         # 만료 (구독 종료)


class Referral(Base):
    """추천 관계 테이블"""
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="추천인 ID")
    referred_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="피추천인 ID")
    
    status = Column(SQLEnum(ReferralStatus), default=ReferralStatus.PENDING, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True, comment="구독 시작 시점")
    
    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referrals_received")
    commissions = relationship("Commission", back_populates="referral")


class CommissionStatus(str, enum.Enum):
    """커미션 상태"""
    PENDING = "PENDING"         # 대기 (발생했지만 홀드백 기간 전)
    HOLDBACK = "HOLDBACK"       # 홀드백 (30일 대기 중)
    APPROVED = "APPROVED"       # 승인 (지급 가능)
    PAID = "PAID"               # 지급 완료
    CANCELLED = "CANCELLED"     # 취소 (환불 등)


class Commission(Base):
    """커미션 내역"""
    __tablename__ = "commissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="커미션 수령자 (추천인)")
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=False, index=True)
    
    # 금액
    amount = Column(Float, nullable=False, comment="커미션 금액")
    currency = Column(String, default="KRW")
    
    # 상태
    status = Column(SQLEnum(CommissionStatus), default=CommissionStatus.PENDING, index=True)
    
    # 홀드백 기간 (30일)
    holdback_until = Column(DateTime, nullable=True, comment="홀드백 종료일 (이후 지급 가능)")
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, comment="커미션 발생일")
    approved_at = Column(DateTime, nullable=True, comment="승인일")
    paid_at = Column(DateTime, nullable=True, comment="지급일")
    
    # 메타데이터
    description = Column(Text, nullable=True, comment="커미션 설명")
    commission_rate_id = Column(Integer, ForeignKey("commission_rates.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="commissions")
    referral = relationship("Referral", back_populates="commissions")
    commission_rate = relationship("CommissionRate", back_populates="commissions")


class SubscriptionPlan(Base):
    """구독 플랜 마스터 테이블 (DB에서 관리)"""
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, comment="플랜 이름 (FREE, BASIC, PRO, ENTERPRISE)")
    display_name = Column(String, nullable=False, comment="표시 이름")
    
    # 가격
    price_monthly = Column(Float, default=0, comment="월 가격")
    price_yearly = Column(Float, default=0, comment="연 가격")
    
    # 기능 제한
    max_conditions = Column(Integer, nullable=True, comment="최대 조건식 수 (null = 무제한)")
    max_stocks = Column(Integer, nullable=True, comment="최대 종목 수")
    
    # 상태
    is_active = Column(Boolean, default=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    commission_rates = relationship("CommissionRate", back_populates="plan")


class CommissionRate(Base):
    """커미션 비율 설정 (DB에서 이벤트별로 관리)"""
    __tablename__ = "commission_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 적용 대상
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True, comment="특정 플랜에만 적용 (null = 전체)")
    event_type = Column(String, nullable=False, comment="이벤트 타입 (SIGNUP, RENEWAL, UPGRADE)")
    
    # 비율
    rate_percentage = Column(Float, nullable=False, comment="커미션 비율 (예: 10.0 = 10%)")
    
    # 유효 기간
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True, comment="null = 무기한")
    
    # 상태
    is_active = Column(Boolean, default=True)
    
    # 설명
    description = Column(Text, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = relationship("SubscriptionPlan", back_populates="commission_rates")
    commissions = relationship("Commission", back_populates="commission_rate")
