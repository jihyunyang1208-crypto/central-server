import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User, Subscription, SubscriptionStatus
from app.models.commission import SubscriptionPlan

db = SessionLocal()
try:
    print(f"\n{'='*80}")
    print("Database Values vs API Response")
    print(f"{'='*80}")
    
    # Get user 1's subscription
    user = db.query(User).filter(User.id == 1).first()
    sub = db.query(Subscription).filter(Subscription.user_id == 1).first()
    
    if sub:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
        
        print(f"\nUser: {user.email}")
        print(f"\nSubscriptionPlan table values:")
        print(f"  plan.id = {plan.id}")
        print(f"  plan.name = '{plan.name}'")  # This is what API should return
        print(f"  plan.display_name = '{plan.display_name}'")  # This is for UI display
        
        print(f"\nWhat API returns (after fix):")
        print(f"  'plan_name': plan.name = '{plan.name}'")
        
        print(f"\nWhat AutoTrader expects:")
        print(f"  'PRO' -> PRO plan")
        print(f"  'STANDARD' -> STANDARD plan")
        print(f"  'FREE' or 'SIMULATION' -> SIMULATION plan")
        
        print(f"\n{'='*80}")
        print(f"MATCH: {plan.name == 'PRO'}")
        print(f"{'='*80}\n")
    else:
        print("No subscription found")
finally:
    db.close()
