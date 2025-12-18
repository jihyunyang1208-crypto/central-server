"""
Toss Payments API Router
Handles payment preparation, confirmation, and webhooks
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import os
import httpx
import logging

from app.models.database import get_db
from app.models.user import Subscription, User
from app.models.commission import SubscriptionPlan
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

# Toss Payments Configuration
TOSS_CLIENT_KEY = os.getenv("TOSS_CLIENT_KEY", "test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq")
TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY", "test_sk_zXLkKEypNArWmo50nX3lmeaxYG5R")
TOSS_API_URL = "https://api.tosspayments.com/v1/payments"

# Request/Response Models
class PaymentPrepareRequest(BaseModel):
    plan_id: int
    billing_period: str  # 'monthly' or 'yearly'

class PaymentPrepareResponse(BaseModel):
    order_id: str
    amount: int
    order_name: str
    customer_email: str
    customer_name: str

class PaymentConfirmRequest(BaseModel):
    payment_key: str
    order_id: str
    amount: int

@router.post("/prepare", response_model=PaymentPrepareResponse)
async def prepare_payment(
    request: PaymentPrepareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    결제 준비 - 주문 정보 생성
    """
    try:
        # current_user is already a User object
        user = current_user
        user_id = user.id
        
        # Get plan info
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == request.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Calculate amount
        amount = plan.price_monthly if request.billing_period == 'monthly' else plan.price_yearly
        
        # Generate unique order ID
        order_id = f"AUT_{user_id}_{int(datetime.now().timestamp())}"
        
        # Create order name
        period_text = "월간" if request.billing_period == 'monthly' else "연간"
        order_name = f"{plan.display_name} {period_text} 구독"
        
        logger.info(f"Payment prepared: {order_id} for user {user_id}, amount: {amount}")
        
        return PaymentPrepareResponse(
            order_id=order_id,
            amount=amount,
            order_name=order_name,
            customer_email=user.email,
            customer_name=user.email.split('@')[0]  # Use email prefix as name
        )
    
    except Exception as e:
        logger.error(f"Payment preparation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
async def confirm_payment(
    request: PaymentConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    결제 승인 - 토스페이먼츠 서버에 결제 승인 요청
    """
    try:
        user_id = current_user.id
        
        # Verify payment with Toss Payments
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TOSS_API_URL}/confirm",
                json={
                    "paymentKey": request.payment_key,
                    "orderId": request.order_id,
                    "amount": request.amount
                },
                auth=(TOSS_SECRET_KEY, ""),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Toss payment confirmation failed: {error_data}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_data.get("message", "Payment confirmation failed")
                )
            
            payment_data = response.json()
        
        # Extract plan_id and billing period from order_id
        # Format: AUT_{user_id}_{timestamp}
        # We need to store plan_id in the order somehow - for now, get from active cart/session
        # This is a simplified version - in production, store order details in DB
        
        # For now, assume Standard plan (id=2) for testing
        plan_id = 2
        billing_period = "monthly"
        
        # Calculate expiration date
        if billing_period == "monthly":
            expires_at = datetime.utcnow() + timedelta(days=30)
        else:  # yearly
            expires_at = datetime.utcnow() + timedelta(days=365)
        
        # Update or create subscription
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).first()
        
        if subscription:
            subscription.plan_id = plan_id
            subscription.status = "ACTIVE"
            subscription.expires_at = expires_at
            subscription.auto_renew = True
        else:
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status="ACTIVE",
                expires_at=expires_at,
                auto_renew=True
            )
            db.add(subscription)
        
        db.commit()
        
        logger.info(f"Subscription activated for user {user_id}, plan {plan_id}")
        
        return {
            "success": True,
            "message": "Payment confirmed and subscription activated",
            "payment_data": payment_data,
            "subscription": {
                "plan_id": plan_id,
                "status": "ACTIVE",
                "expires_at": expires_at.isoformat()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment confirmation error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """
    토스페이먼츠 웹훅 처리
    """
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        
        # Verify webhook signature (in production)
        # For now, just log it
        
        event_type = body.get("eventType")
        payment_data = body.get("data")
        
        if event_type == "PAYMENT_STATUS_CHANGED":
            # Handle payment status changes
            status = payment_data.get("status")
            order_id = payment_data.get("orderId")
            
            logger.info(f"Payment status changed: {order_id} -> {status}")
            
            # Update subscription status if needed
            # This is a simplified version
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"success": False, "error": str(e)}
