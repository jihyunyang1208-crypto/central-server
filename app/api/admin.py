"""
Admin API endpoints
Provides statistics and analytics for admin dashboard
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.core.database import get_db
from app.middleware.admin import require_admin
from app.models.user import User, Subscription
from app.models.commission import Commission, Referral

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/stats/overview")
async def get_overview_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get overall system statistics
    Requires admin privileges
    """
    # Total users
    total_users = db.query(func.count(User.id)).scalar()
    
    # Active users today
    today = datetime.utcnow().date()
    active_today = db.query(func.count(User.id)).filter(
        func.date(User.last_active_at) == today
    ).scalar()
    
    # Total active subscriptions
    total_subscriptions = db.query(func.count(Subscription.id)).filter(
        Subscription.status == "ACTIVE"
    ).scalar()
    
    # Monthly revenue (current month)
    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.query(func.sum(Subscription.amount)).filter(
        and_(
            Subscription.status == "ACTIVE",
            Subscription.created_at >= current_month_start
        )
    ).scalar() or 0
    
    # Pending commissions
    pending_commissions = db.query(func.sum(Commission.amount)).filter(
        Commission.status == "PENDING"
    ).scalar() or 0
    
    return {
        "total_users": total_users or 0,
        "active_users_today": active_today or 0,
        "total_subscriptions": total_subscriptions or 0,
        "monthly_revenue": float(monthly_revenue),
        "total_commissions_pending": float(pending_commissions)
    }

@router.get("/stats/subscriptions")
async def get_subscription_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, Dict[str, Any]]:
    """
    Get subscription breakdown by plan
    """
    # Get total active subscriptions
    total = db.query(func.count(Subscription.id)).filter(
        Subscription.status == "ACTIVE"
    ).scalar() or 1  # Avoid division by zero
    
    # Get count by plan
    plan_counts = db.query(
        Subscription.plan_name,
        func.count(Subscription.id).label('count')
    ).filter(
        Subscription.status == "ACTIVE"
    ).group_by(Subscription.plan_name).all()
    
    result = {}
    for plan_name, count in plan_counts:
        result[plan_name] = {
            "count": count,
            "percentage": round((count / total) * 100, 1)
        }
    
    # Ensure all plans are represented
    for plan in ["FREE", "BASIC", "PRO", "ENTERPRISE"]:
        if plan not in result:
            result[plan] = {"count": 0, "percentage": 0.0}
    
    return result

@router.get("/stats/users")
async def get_user_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get user statistics
    """
    # Total users
    total = db.query(func.count(User.id)).scalar() or 0
    
    # Active today
    today = datetime.utcnow().date()
    active_today = db.query(func.count(User.id)).filter(
        func.date(User.last_active_at) == today
    ).scalar() or 0
    
    # Active this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_week = db.query(func.count(User.id)).filter(
        User.last_active_at >= week_ago
    ).scalar() or 0
    
    # New this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_month = db.query(func.count(User.id)).filter(
        User.created_at >= month_start
    ).scalar() or 0
    
    return {
        "total": total,
        "active_today": active_today,
        "active_this_week": active_week,
        "new_this_month": new_month,
        "churn_rate": 0.0  # TODO: Calculate actual churn rate
    }

@router.get("/stats/revenue")
async def get_revenue_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get revenue statistics by month
    """
    # Last 6 months revenue
    months_data = []
    for i in range(6):
        month_start = (datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) 
                      - timedelta(days=30 * i))
        month_end = month_start + timedelta(days=30)
        
        revenue = db.query(func.sum(Subscription.amount)).filter(
            and_(
                Subscription.status == "ACTIVE",
                Subscription.created_at >= month_start,
                Subscription.created_at < month_end
            )
        ).scalar() or 0
        
        months_data.append({
            "month": month_start.strftime("%Y-%m"),
            "revenue": float(revenue)
        })
    
    return {
        "monthly_data": list(reversed(months_data))
    }

@router.get("/users")
async def get_users_list(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get paginated list of users
    """
    offset = (page - 1) * limit
    
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(func.count(User.id)).scalar()
    
    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
                "referral_code": user.referral_code
            }
            for user in users
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    is_admin: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, str]:
    """
    Update user admin status
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_admin = is_admin
    db.commit()
    
    return {"message": f"User admin status updated to {is_admin}"}
