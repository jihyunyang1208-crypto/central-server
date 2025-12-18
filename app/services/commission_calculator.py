# central-backend/app/services/commission_calculator.py
"""
커미션 계산 및 상태 관리 서비스
- 자동화된 상태 전이 (PENDING → HOLDBACK → APPROVED)
- 홀드백 기간 검증 (30일)
- 트랜잭션 롤백 기능
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from ..models.commission import (
    Commission,
    CommissionStatus,
    CommissionRate,
    Referral,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


def trigger_commission_event(
    db: Session,
    referral_id: int,
    event_type: str,  # SIGNUP, RENEWAL, UPGRADE
    subscription_amount: float
):
    """
    커미션 발생 이벤트 처리
    - 커미션 비율 조회 (DB에서)
    - 커미션 생성 (PENDING 상태)
    - 홀드백 기간 설정 (30일)
    """
    try:
        # 추천 관계 조회
        referral = db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            logger.error(f"Referral {referral_id} not found")
            return
        
        # 커미션 비율 조회 (활성화된 것 중 가장 최근 것)
        commission_rate = db.query(CommissionRate).filter(
            CommissionRate.event_type == event_type,
            CommissionRate.is_active == True,
            CommissionRate.valid_from <= datetime.utcnow(),
            (CommissionRate.valid_until.is_(None)) | (CommissionRate.valid_until >= datetime.utcnow())
        ).order_by(CommissionRate.created_at.desc()).first()
        
        if not commission_rate:
            logger.warning(f"No active commission rate found for event {event_type}")
            # 기본 비율 10% 사용
            rate_percentage = 10.0
            commission_rate_id = None
        else:
            rate_percentage = commission_rate.rate_percentage
            commission_rate_id = commission_rate.id
        
        # 커미션 금액 계산
        commission_amount = subscription_amount * (rate_percentage / 100)
        
        # 홀드백 종료일 계산 (30일 후)
        holdback_until = datetime.utcnow() + timedelta(days=settings.COMMISSION_HOLDBACK_DAYS)
        
        # 커미션 생성
        new_commission = Commission(
            user_id=referral.referrer_id,
            referral_id=referral.id,
            amount=commission_amount,
            currency="KRW",
            status=CommissionStatus.PENDING,
            holdback_until=holdback_until,
            description=f"{event_type} commission for referral #{referral.id}",
            commission_rate_id=commission_rate_id,
        )
        
        db.add(new_commission)
        db.commit()
        
        logger.info(
            f"Commission created: {commission_amount} KRW for user {referral.referrer_id} "
            f"(event: {event_type}, holdback until: {holdback_until})"
        )
        
    except Exception as e:
        logger.error(f"Failed to create commission: {e}")
        db.rollback()
        raise


def process_commission_state_transitions(db: Session):
    """
    커미션 상태 자동 전이 (스케줄러에서 호출)
    - PENDING → HOLDBACK: 즉시
    - HOLDBACK → APPROVED: 홀드백 기간 종료 후
    """
    try:
        # PENDING → HOLDBACK
        pending_commissions = db.query(Commission).filter(
            Commission.status == CommissionStatus.PENDING
        ).all()
        
        for commission in pending_commissions:
            commission.status = CommissionStatus.HOLDBACK
        
        if pending_commissions:
            db.commit()
            logger.info(f"Transitioned {len(pending_commissions)} commissions to HOLDBACK")
        
        # HOLDBACK → APPROVED (홀드백 기간 종료)
        now = datetime.utcnow()
        holdback_commissions = db.query(Commission).filter(
            Commission.status == CommissionStatus.HOLDBACK,
            Commission.holdback_until <= now
        ).all()
        
        for commission in holdback_commissions:
            commission.status = CommissionStatus.APPROVED
            commission.approved_at = now
        
        if holdback_commissions:
            db.commit()
            logger.info(f"Approved {len(holdback_commissions)} commissions after holdback period")
        
    except Exception as e:
        logger.error(f"Commission state transition failed: {e}")
        db.rollback()
        raise


def cancel_commission(db: Session, commission_id: int, reason: str = "Refund"):
    """
    커미션 취소 (환불 등의 이유로)
    - 트랜잭션 롤백 기능
    """
    try:
        commission = db.query(Commission).filter(Commission.id == commission_id).first()
        
        if not commission:
            raise ValueError(f"Commission {commission_id} not found")
        
        if commission.status == CommissionStatus.PAID:
            raise ValueError("Cannot cancel already paid commission")
        
        commission.status = CommissionStatus.CANCELLED
        commission.description = f"{commission.description} | CANCELLED: {reason}"
        
        db.commit()
        logger.info(f"Commission {commission_id} cancelled: {reason}")
        
    except Exception as e:
        logger.error(f"Failed to cancel commission: {e}")
        db.rollback()
        raise
