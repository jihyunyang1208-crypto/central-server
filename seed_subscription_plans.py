# central-backend/seed_subscription_plans.py
"""
구독 플랜 시드 데이터 생성 스크립트
FREE, STANDARD, PRO 플랜을 데이터베이스에 추가합니다.
"""
from app.models.database import SessionLocal
from app.models.commission import SubscriptionPlan

def seed_plans():
    db = SessionLocal()
    
    try:
        # 기존 플랜 확인
        existing_plans = db.query(SubscriptionPlan).all()
        if existing_plans:
            print(f"[OK] {len(existing_plans)} plans already exist:")
            for plan in existing_plans:
                print(f"   - {plan.name}: {plan.display_name}")
            return
        
        # 플랜 데이터
        plans = [
            {
                "name": "FREE",
                "display_name": "무료 플랜",
                "price_monthly": 0,
                "price_yearly": 0,
                "max_conditions": 1,
                "max_stocks": 10,
                "is_active": True,
            },
            {
                "name": "STANDARD",
                "display_name": "스탠다드",
                "price_monthly": 29000,
                "price_yearly": 278400,  # 20% 할인
                "max_conditions": 3,
                "max_stocks": 50,
                "is_active": True,
            },
            {
                "name": "PRO",
                "display_name": "프로",
                "price_monthly": 99000,
                "price_yearly": 950400,  # 20% 할인
                "max_conditions": 10,
                "max_stocks": 200,
                "is_active": True,
            },
        ]
        
        # 플랜 생성
        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)
        
        db.commit()
        print(f"[OK] Successfully created {len(plans)} subscription plans!")
        
        # 생성된 플랜 확인
        created_plans = db.query(SubscriptionPlan).all()
        for plan in created_plans:
            print(f"   - {plan.name} (ID: {plan.id}): {plan.price_monthly:,}won/month")
            
    except Exception as e:
        print(f"[ERROR] Error seeding plans: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_plans()
