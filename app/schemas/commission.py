# central-backend/app/schemas/commission.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models.commission import CommissionStatus


class CommissionResponse(BaseModel):
    id: int
    amount: float
    currency: str
    status: CommissionStatus
    holdback_until: Optional[datetime]
    created_at: datetime
    approved_at: Optional[datetime]
    paid_at: Optional[datetime]
    description: Optional[str]
    
    class Config:
        from_attributes = True


class CommissionStatsResponse(BaseModel):
    total_pending: float
    total_holdback: float
    total_approved: float
    total_paid: float
    total_referrals: int
    active_referrals: int
