import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.commission import SubscriptionPlan

db = SessionLocal()
try:
    plans = db.query(SubscriptionPlan).all()
    print(f"\n{'='*80}")
    print("Subscription Plans in Database")
    print(f"{'='*80}")
    
    for plan in plans:
        print(f"\nPlan ID: {plan.id}")
        print(f"  name: {plan.name}")
        print(f"  display_name: {plan.display_name}")
        print(f"  is_active: {plan.is_active}")
    
    print(f"\n{'='*80}\n")
finally:
    db.close()
