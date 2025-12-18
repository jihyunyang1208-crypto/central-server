# central-backend/app/services/auto_payment.py
"""
Auto-Payment Service
Handles automatic subscription renewal payments using billing keys
"""
import httpx
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import Subscription, User
from app.models.database import get_db
import os

logger = logging.getLogger(__name__)

TOSS_API_URL = "https://api.tosspayments.com/v1"
TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")


async def process_auto_payment(subscription_id: int, db: Session) -> bool:
    """
    자동 결제 처리
    
    Args:
        subscription_id: 구독 ID
        db: Database session
    
    Returns:
        bool: 성공 여부
    """
    try:
        subscription = db.query(Subscription).get(subscription_id)
        
        if not subscription or not subscription.billing_key:
            logger.warning(f"No billing key for subscription {subscription_id}")
            return False
        
        # Get plan info
        plan = subscription.plan
        amount = plan.price_monthly if subscription.billing_period == 'monthly' else plan.price_yearly
        
        # Generate order ID
        order_id = f"AUTO_{subscription.id}_{int(datetime.now().timestamp())}"
        order_name = f"{plan.display_name} 자동결제"
        
        # Request payment with billing key
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TOSS_API_URL}/billing/{subscription.billing_key}",
                json={
                    "customerKey": str(subscription.user_id),
                    "amount": amount,
                    "orderId": order_id,
                    "orderName": order_name,
                    "customerEmail": subscription.user.email if subscription.user else None
                },
                auth=(TOSS_SECRET_KEY, ""),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                payment_data = response.json()
                
                # Extend subscription
                if subscription.billing_period == 'monthly':
                    subscription.expires_at = datetime.utcnow() + timedelta(days=30)
                    subscription.next_payment_date = subscription.expires_at
                else:  # yearly
                    subscription.expires_at = datetime.utcnow() + timedelta(days=365)
                    subscription.next_payment_date = subscription.expires_at
                
                subscription.last_payment_at = datetime.utcnow()
                subscription.status = "ACTIVE"
                
                db.commit()
                
                logger.info(f"✅ Auto payment successful for subscription {subscription_id}, amount: {amount}")
                return True
            else:
                logger.error(f"❌ Auto payment failed for subscription {subscription_id}: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Auto payment error for subscription {subscription_id}: {e}", exc_info=True)
        return False


async def check_and_process_renewals(db: Session):
    """
    만료 예정 구독 확인 및 자동 결제 처리
    """
    try:
        # 3일 이내 만료 예정 구독 조회
        threshold_date = datetime.utcnow() + timedelta(days=3)
        
        expiring_subscriptions = db.query(Subscription).filter(
            Subscription.auto_renew == True,
            Subscription.billing_key.isnot(None),
            Subscription.expires_at <= threshold_date,
            Subscription.expires_at > datetime.utcnow(),  # Not yet expired
            Subscription.status == "ACTIVE"
        ).all()
        
        logger.info(f"Found {len(expiring_subscriptions)} subscriptions to renew")
        
        success_count = 0
        fail_count = 0
        
        for subscription in expiring_subscriptions:
            success = await process_auto_payment(subscription.id, db)
            
            if success:
                success_count += 1
                logger.info(f"Renewed subscription {subscription.id}")
            else:
                fail_count += 1
                logger.error(f"Failed to renew subscription {subscription.id}")
                # TODO: Send notification to user about payment failure
        
        logger.info(f"Renewal check complete: {success_count} succeeded, {fail_count} failed")
        
    except Exception as e:
        logger.error(f"Renewal check failed: {e}", exc_info=True)
