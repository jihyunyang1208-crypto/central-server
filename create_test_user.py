# central-backend/create_test_user.py
"""
중앙 서버에 사용자 생성/관리 스크립트
구독 플랜 및 기간 선택 가능
"""
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import SessionLocal
from app.models.user import User, Subscription, SubscriptionStatus
from app.models.commission import SubscriptionPlan
from app.core.security import get_password_hash


def list_users():
    """등록된 사용자 목록 조회"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("\n[INFO] No users found")
            return
        
        print("\n" + "="*80)
        print("Registered Users")
        print("="*80)
        for user in users:
            sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            sub_info = "No subscription"
            if sub:
                plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
                expires = sub.expires_at.strftime('%Y-%m-%d') if sub.expires_at else 'N/A'
                sub_info = f"{plan.display_name} (expires: {expires})"
            
            print(f"ID: {user.id} | Email: {user.email} | {sub_info}")
        print("="*80)
    finally:
        db.close()


def create_or_update_user():
    """사용자 생성 또는 업데이트"""
    db = SessionLocal()
    
    try:
        # 사용자 정보 입력
        print("\n" + "="*80)
        print("User Information")
        print("="*80)
        email = input("Email: ").strip()
        if not email:
            print("[ERROR] Email is required")
            return
        
        password = input("Password: ").strip()
        if not password:
            print("[ERROR] Password is required")
            return
        
        # 기존 사용자 확인
        existing_user = db.query(User).filter(User.email == email).first()
        
        if existing_user:
            print(f"\n[INFO] User {email} already exists (ID: {existing_user.id})")
            update = input("Update password? (y/n): ").strip().lower()
            if update == 'y':
                existing_user.hashed_password = get_password_hash(password)
                db.commit()
                print("[OK] Password updated")
            user = existing_user
        else:
            # 새 사용자 생성
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                referral_code=f"USER{datetime.now().strftime('%Y%m%d%H%M%S')}",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[OK] User created: {email} (ID: {user.id})")
        
        # 구독 플랜 선택
        print("\n" + "="*80)
        print("Subscription Plans")
        print("="*80)
        plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
        
        if not plans:
            print("[ERROR] No subscription plans found. Run init_db.py first!")
            return
        
        for idx, plan in enumerate(plans, 1):
            print(f"{idx}. {plan.display_name} ({plan.name}) - {plan.price_monthly:,}원/월")
        
        plan_choice = input(f"\nSelect plan (1-{len(plans)}): ").strip()
        try:
            plan_idx = int(plan_choice) - 1
            if plan_idx < 0 or plan_idx >= len(plans):
                raise ValueError()
            selected_plan = plans[plan_idx]
        except:
            print("[ERROR] Invalid plan selection")
            return
        
        # 구독 기간 입력
        print("\n" + "="*80)
        print("Subscription Duration")
        print("="*80)
        duration_days = input("Duration (days, default: 30): ").strip()
        try:
            duration_days = int(duration_days) if duration_days else 30
        except:
            duration_days = 30
        
        # 기존 구독 확인 및 생성/업데이트
        existing_sub = db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()
        
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        if existing_sub:
            # 구독 업데이트
            existing_sub.plan_id = selected_plan.id
            existing_sub.status = SubscriptionStatus.ACTIVE
            existing_sub.started_at = datetime.utcnow()
            existing_sub.expires_at = expires_at
            existing_sub.last_payment_at = datetime.utcnow()
            print(f"[OK] Subscription updated")
        else:
            # 새 구독 생성
            subscription = Subscription(
                user_id=user.id,
                plan_id=selected_plan.id,
                status=SubscriptionStatus.ACTIVE,
                started_at=datetime.utcnow(),
                expires_at=expires_at,
                last_payment_at=datetime.utcnow()
            )
            db.add(subscription)
            print(f"[OK] Subscription created")
        
        db.commit()
        
        print("\n" + "="*80)
        print("✅ User Ready!")
        print("="*80)
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Plan: {selected_plan.display_name}")
        print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """메인 메뉴"""
    while True:
        print("\n" + "="*80)
        print("Central Server User Management")
        print("="*80)
        print("1. Create/Update User")
        print("2. List Users")
        print("3. Exit")
        print("="*80)
        
        choice = input("Select option: ").strip()
        
        if choice == '1':
            create_or_update_user()
        elif choice == '2':
            list_users()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("[ERROR] Invalid option")


if __name__ == "__main__":
    main()
