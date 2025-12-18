# central-backend/app/schemas/subscription.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models.user import SubscriptionStatus


class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    price_monthly: float
    price_yearly: float
    max_conditions: Optional[int]
    max_stocks: Optional[int]
    is_active: bool
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan: SubscriptionPlanResponse
    status: SubscriptionStatus
    started_at: Optional[datetime]
    expires_at: Optional[datetime]
    auto_renew: bool
    
    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    plan_id: int
    payment_method_id: Optional[str] = None


class SubscriptionUpgrade(BaseModel):
    new_plan_id: int
