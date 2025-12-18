import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import SessionLocal
from app.models.user import User, Subscription, SubscriptionStatus
from app.models.commission import SubscriptionPlan

db = SessionLocal()
try:
    users = db.query(User).all()
    print(f"\n{'='*80}")
    print("Current Users and Subscriptions")
    print(f"{'='*80}")
    
    for user in users:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        print(f"\nUser ID: {user.id}")
        print(f"Email: {user.email}")
        
        if sub:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
            print(f"Subscription Status: {sub.status}")
            print(f"Plan: {plan.display_name if plan else 'Unknown'} ({plan.name if plan else 'N/A'})")
            print(f"Expires: {sub.expires_at}")
        else:
            print("Subscription: None")
    
    print(f"\n{'='*80}\n")
finally:
    db.close()
