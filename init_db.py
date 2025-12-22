# central-backend/init_db.py
"""
데이터베이스 초기화 스크립트
- 모든 테이블 생성
- 초기 데이터 삽입
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import init_db, SessionLocal
from app.models.commission import SubscriptionPlan, CommissionRate
from datetime import datetime


def create_initial_data():
    """초기 데이터 생성"""
    db = SessionLocal()
    
    try:
        # 구독 플랜 생성
        plans = [
            SubscriptionPlan(
                name="SIM",
                display_name="시뮬레이터",
                price_monthly=8900,
                price_yearly=89000,
                max_conditions=3,
                max_stocks=10,
                is_active=True
            ),
            SubscriptionPlan(
                name="BASIC",
                display_name="베이직",
                price_monthly=29000,
                price_yearly=290000,
                max_conditions=10,
                max_stocks=50,
                is_active=True
            ),
            SubscriptionPlan(
                name="PRO",
                display_name="프로",
                price_monthly=99000,
                price_yearly=990000,
                max_conditions=None,  # Unlimited
                max_stocks=None,  # Unlimited
                is_active=True
            ),
        ]
        
        # 기존 플랜 확인
        existing_plans = db.query(SubscriptionPlan).count()
        if existing_plans == 0:
            db.add_all(plans)
            print("[OK] Subscription plans created")
        else:
            print("[INFO] Subscription plans already exist")
        
        # 커미션 비율 생성
        rates = [
            CommissionRate(
                event_type="SIGNUP",
                rate_percentage=4.0,
                is_active=True,
                description="신규 가입 시 4% 커미션"
            ),
            CommissionRate(
                event_type="RENEWAL",
                rate_percentage=3.0,
                is_active=True,
                description="구독 갱신 시 3% 커미션"
            ),
            CommissionRate(
                event_type="UPGRADE",
                rate_percentage=4.0,
                is_active=True,
                description="플랜 업그레이드 시 4% 커미션"
            ),
        ]
        
        # 기존 커미션 비율 확인
        existing_rates = db.query(CommissionRate).count()
        if existing_rates == 0:
            db.add_all(rates)
            print("[OK] Commission rates created")
        else:
            print("[INFO] Commission rates already exist")
        
        db.commit()
        print("[OK] Initial data created successfully")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to create initial data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("[DB Init] Starting database initialization...")
    
    # 테이블 생성
    init_db()
    print("[DB Init] Tables created successfully")
    
    # 초기 데이터 생성
    create_initial_data()
    
    print("[DB Init] Database initialization complete!")
