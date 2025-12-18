# central-backend/rebuild_db.py
"""
데이터베이스 완전 재생성
- 모든 테이블 DROP
- 모든 테이블 CREATE
- 초기 데이터 INSERT
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database URL
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "0509")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aut_db")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"[DB Rebuild] Connecting to: {DATABASE_URL}")
print("[DB Rebuild] WARNING: This will DELETE ALL DATA!")
print("[DB Rebuild] Press Ctrl+C to cancel...")

import time
time.sleep(3)

engine = create_engine(DATABASE_URL)

print("\n[DB Rebuild] Starting database rebuild...")

try:
    with engine.connect() as conn:
        # 1. DROP all tables (in reverse dependency order)
        print("\n[Step 1/3] Dropping all tables...")
        drop_statements = [
            "DROP TABLE IF EXISTS commissions CASCADE;",
            "DROP TABLE IF EXISTS commission_rates CASCADE;",
            "DROP TABLE IF EXISTS referrals CASCADE;",
            "DROP TABLE IF EXISTS trading_settings CASCADE;",
            "DROP TABLE IF EXISTS kiwoom_credentials CASCADE;",
            "DROP TABLE IF EXISTS subscriptions CASCADE;",
            "DROP TABLE IF EXISTS subscription_plans CASCADE;",
            "DROP TABLE IF EXISTS users CASCADE;",
            "DROP TYPE IF EXISTS subscriptionstatus CASCADE;",
            "DROP TYPE IF EXISTS referralstatus CASCADE;",
            "DROP TYPE IF EXISTS commissionstatus CASCADE;",
        ]
        
        for stmt in drop_statements:
            conn.execute(text(stmt))
            conn.commit()
        
        print("[Step 1/3] All tables dropped successfully")
        
        # 2. Create all tables using SQLAlchemy models
        print("\n[Step 2/3] Creating all tables from models...")
        from app.models.database import Base, init_db
        
        # Import all models to register them with Base
        from app.models import user, commission, kiwoom, trading_settings
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("[Step 2/3] All tables created successfully")
        
        # 3. Insert initial data
        print("\n[Step 3/3] Inserting initial data...")
        
        # Subscription Plans
        plans_sql = """
        INSERT INTO subscription_plans (name, display_name, price_monthly, price_yearly, max_conditions, max_stocks, is_active)
        VALUES 
            ('FREE', '무료', 0, 0, 3, 10, true),
            ('STANDARD', '스탠다드', 29000, 290000, 10, 50, true),
            ('PRO', '프로', 59000, 590000, NULL, NULL, true)
        ON CONFLICT (name) DO NOTHING;
        """
        conn.execute(text(plans_sql))
        conn.commit()
        print("  - Subscription plans inserted")
        
        # Commission Rates
        rates_sql = """
        INSERT INTO commission_rates (plan_id, event_type, rate_percentage, is_active, description)
        SELECT 
            sp.id,
            'SIGNUP',
            CASE 
                WHEN sp.name = 'STANDARD' THEN 10.0
                WHEN sp.name = 'PRO' THEN 15.0
                ELSE 0.0
            END,
            true,
            CASE 
                WHEN sp.name = 'STANDARD' THEN '스탠다드 플랜 가입 커미션 10%'
                WHEN sp.name = 'PRO' THEN '프로 플랜 가입 커미션 15%'
                ELSE 'FREE 플랜 (커미션 없음)'
            END
        FROM subscription_plans sp
        WHERE sp.name IN ('FREE', 'STANDARD', 'PRO')
        ON CONFLICT DO NOTHING;
        """
        conn.execute(text(rates_sql))
        conn.commit()
        print("  - Commission rates inserted")
        
        print("\n[DB Rebuild] Database rebuild completed successfully!")
        print("\nDatabase Schema:")
        print("  - users")
        print("  - subscriptions")
        print("  - subscription_plans (3 plans)")
        print("  - referrals")
        print("  - commissions")
        print("  - commission_rates")
        print("  - kiwoom_credentials")
        print("  - trading_settings")
        
except Exception as e:
    print(f"\n[DB Rebuild] Error: {e}")
    raise
