# central-backend/app/models/community.py
"""
커뮤니티 페이지 관련 SQLAlchemy 모델
- CommunityPost: 공유 게시글 (조건식, 전략 등)
- Comment: 댓글
- UserCredit: 사용자 크레딧 잔액
- CreditHistory: 크레딧 거래 내역
- PaidAccess: 유료 게시글 열람 기록
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text,
    ForeignKey, JSON, Enum
)
import enum
from ..core.database import Base


def _now():
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────

class PostType(str, enum.Enum):
    CONDITION = "condition"    # 조건식 공유
    STRATEGY  = "strategy"    # 전략 공유
    ANALYSIS  = "analysis"    # 분석 공유
    FREE      = "free"        # 자유 게시글


class VerificationStatus(str, enum.Enum):
    NONE      = "none"        # 미검증
    PENDING   = "pending"     # 검증 대기 중
    VERIFIED  = "verified"    # 검증 완료
    FAILED    = "failed"      # 검증 실패


class CreditEventType(str, enum.Enum):
    RECHARGE  = "recharge"    # 충전 (결제)
    SPEND     = "spend"       # 사용 (유료 게시글 열람)
    REFUND    = "refund"      # 환불
    REWARD    = "reward"      # 보상 (이벤트 등)


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────

class CommunityPost(Base):
    """커뮤니티 게시글"""
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)

    # 작성자 (central-backend User ID)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 게시글 기본 정보
    title   = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String(20), default=PostType.FREE.value, index=True)

    # 조건식/전략 연결 (선택)
    condition_id   = Column(String(50), nullable=True, comment="로컬 봇 조건식 seq")
    condition_name = Column(String(100), nullable=True, comment="조건식명")

    # 수익 인증 데이터 (AutoTrader 봇에서 생성된 패키지)
    verification_status  = Column(String(20), default=VerificationStatus.NONE.value, index=True)
    verification_payload = Column(JSON, nullable=True, comment="인증 패키지 (수익률, 거래 내역 등)")
    verified_at          = Column(DateTime, nullable=True)

    # 요약 지표 (프리뷰용 - 인증된 경우 채워짐)
    win_rate       = Column(Float, nullable=True, comment="승률 (0.0~1.0)")
    total_pnl      = Column(Float, nullable=True, comment="총 실현 손익 (원)")
    roi_avg        = Column(Float, nullable=True, comment="평균 수익률 (%)")
    trades_count   = Column(Integer, nullable=True, comment="총 거래 횟수")

    # 유료 설정
    is_paid       = Column(Boolean, default=False, comment="유료 게시글 여부")
    credit_price  = Column(Integer, default=0, comment="열람 크레딧 가격")

    # 공개 설정
    is_hidden  = Column(Boolean, default=False, comment="숨김 처리")
    is_deleted = Column(Boolean, default=False, comment="소프트 삭제")

    # 통계
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class Comment(Base):
    """게시글 댓글"""
    __tablename__ = "community_comments"

    id      = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content   = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class UserCredit(Base):
    """사용자 크레딧 잔액 (1크레딧 ≈ 100원 기준)"""
    __tablename__ = "user_credits"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=0, comment="현재 크레딧 잔액")
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class CreditHistory(Base):
    """크레딧 거래 내역"""
    __tablename__ = "credit_histories"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, comment="recharge/spend/refund/reward")
    amount     = Column(Integer, nullable=False, comment="변화량 (양수: 증가, 음수: 감소)")
    balance_after = Column(Integer, nullable=False, comment="처리 후 잔액")

    # 참조 정보
    post_id      = Column(Integer, ForeignKey("community_posts.id"), nullable=True, comment="구매한 게시글 ID")
    payment_key  = Column(String(100), nullable=True, comment="토스 결제 키 (충전 시)")
    description  = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=_now)


class PaidAccess(Base):
    """유료 게시글 열람 기록"""
    __tablename__ = "paid_accesses"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False, index=True)
    credits_spent = Column(Integer, nullable=False, comment="사용된 크레딧")
    accessed_at   = Column(DateTime, default=_now)
