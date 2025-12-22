"""
테스트 데이터 생성 스크립트
jihyun.yang.1208@gmail.com 계정으로 테스트 사용자 및 구독 생성
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User, Subscription, SubscriptionStatus
from app.models.commission import SubscriptionPlan, Referral, ReferralStatus
from app.core.security import get_password_hash
from datetime import datetime, timedelta
import uuid

def create_test_data():
    db = SessionLocal()
    
    try:
        # 1. 테스트 이메일로 기존 사용자 확인
        test_email = "jihyun.yang.1208@gmail.com"
        existing_user = db.query(User).filter(User.email == test_email).first()
        
        if existing_user:
            print(f"[OK] User already exists: {test_email} (ID: {existing_user.id})")
            user = existing_user
        else:
            # 2. 새 사용자 생성
            user = User(
                email=test_email,
                hashed_password=get_password_hash("test1234"),  # 테스트 비밀번호
                is_active=True,
                is_admin=False,
                referral_code=str(uuid.uuid4())[:8].upper(),
                created_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[OK] Created test user: {test_email} (ID: {user.id})")
        
        # 3. PRO 플랜 조회
        pro_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.name == "PRO"
        ).first()
        
        if not pro_plan:
            print("[ERROR] PRO plan not found. Please run seed_subscription_plans.py first.")
            return
        
        # 4. 기존 활성 구독 확인
        existing_subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        if existing_subscription:
            print(f"[OK] Active subscription already exists (expires: {existing_subscription.expires_at})")
        else:
            # 5. 새 구독 생성 (30일)
            subscription = Subscription(
                user_id=user.id,
                plan_name="PRO",
                amount=pro_plan.price,
                status=SubscriptionStatus.ACTIVE,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
                auto_renew=True,
                created_at=datetime.utcnow()
            )
            db.add(subscription)
            db.commit()
            print(f"[OK] Created PRO subscription (expires: {subscription.expires_at})")
        
        # 6. 요약 정보 출력
        print("\n" + "="*60)
        print("TEST DATA SUMMARY")
        print("="*60)
        print(f"Email: {user.email}")
        print(f"Password: test1234")
        print(f"User ID: {user.id}")
        print(f"Referral Code: {user.referral_code}")
        print(f"Plan: PRO")
        print(f"Status: ACTIVE")
        
        active_sub = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        if active_sub:
            print(f"Expires: {active_sub.expires_at}")
            print(f"Auto Renew: {active_sub.auto_renew}")
        
        print("="*60)
        print("\n[SUCCESS] Test data created successfully!")
        print("\nLogin credentials:")
        print(f"   Email: {test_email}")
        print(f"   Password: test1234")
        
    except Exception as e:
        print(f"[ERROR] Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()
