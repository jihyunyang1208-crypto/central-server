# central-backend/app/routers/billing.py
"""
Billing Router - Auto-renewal billing management
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
from datetime import datetime, timedelta
import os
import logging

from ..core.database import get_db
from ..models.user import User, Subscription
from ..core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

TOSS_API_URL = "https://api.tosspayments.com/v1"
TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")


class BillingKeyRequest(BaseModel):
    auth_key: str
    customer_key: str


@router.post("/register")
async def register_billing_key(
    request: BillingKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    빌링키 등록
    - 최초 카드 등록 시 호출
    - authKey를 billingKey로 교환
    """
    try:
        # 1. Issue billing key from Toss
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TOSS_API_URL}/billing/authorizations/issue",
                json={
                    "authKey": request.auth_key,
                    "customerKey": request.customer_key
                },
                auth=(TOSS_SECRET_KEY, ""),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"Billing key issue failed: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Billing key issue failed: {response.text}"
                )
            
            billing_data = response.json()
        
        # 2. Save billing key to DB
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        subscription.billing_key = billing_data["billingKey"]
        subscription.auto_renew = True
        
        # Extract card info
        card_info = billing_data.get("card", {})
        subscription.card_last4 = card_info.get("number", "")[-4:] if card_info.get("number") else None
        subscription.card_company = card_info.get("company", "")
        subscription.next_payment_date = subscription.expires_at
        
        db.commit()
        
        logger.info(f"✅ Billing key registered for user {current_user.id}")
        
        return {
            "success": True,
            "billing_key": billing_data["billingKey"],
            "card_info": {
                "last4": subscription.card_last4,
                "company": subscription.card_company
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Billing key registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel")
async def cancel_auto_renew(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """자동결제 해지"""
    try:
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        subscription.auto_renew = False
        subscription.billing_key = None
        subscription.next_payment_date = None
        
        db.commit()
        
        logger.info(f"✅ Auto-renewal cancelled for user {current_user.id}")
        
        return {"success": True, "message": "Auto-renewal cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-renewal cancellation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_billing_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """빌링 정보 조회"""
    try:
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        if not subscription:
            return {
                "auto_renew": False,
                "card_last4": None,
                "card_company": None,
                "next_payment_date": None
            }
        
        return {
            "auto_renew": subscription.auto_renew or False,
            "card_last4": subscription.card_last4,
            "card_company": subscription.card_company,
            "next_payment_date": subscription.next_payment_date.isoformat() if subscription.next_payment_date else None,
            "billing_period": subscription.billing_period or 'monthly'
        }
        
    except Exception as e:
        logger.error(f"Failed to get billing info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
