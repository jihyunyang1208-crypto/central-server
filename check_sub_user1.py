from app.core.database import SessionLocal
from app.models.user import User, Subscription
from app.models.commission import SubscriptionPlan

db = SessionLocal()
try:
    user_id = 1
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"User {user_id} not found")
    else:
        print(f"User: {user.email} (ID: {user.id})")
        if user.subscription:
            sub = user.subscription
            plan = sub.plan
            print(f"Subscription Status: {sub.status}")
            print(f"Plan: {plan.name} (Display: {plan.display_name})")
            print(f"Expires At: {sub.expires_at}")
        else:
            print("No Subscription found (Defaults to FREE/SIMULATION)")
finally:
    db.close()
