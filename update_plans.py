# central-backend/update_plans.py
"""
구독 플랜 업데이트
- FREE 제거
- SIMULATION 추가 (6,900원, 시뮬레이터 전용)
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "0509")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aut_db")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"[Plan Update] Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        print("\n[Step 1/3] Deleting old plans...")
        
        # Delete old plans
        conn.execute(text("DELETE FROM commission_rates;"))
        conn.execute(text("DELETE FROM subscription_plans;"))
        conn.commit()
        print("  - Old plans deleted")
        
        print("\n[Step 2/3] Creating new plans...")
        
        # Insert new plans
        plans_sql = """
        INSERT INTO subscription_plans (name, display_name, price_monthly, price_yearly, max_conditions, max_stocks, is_active)
        VALUES 
            ('SIMULATION', '시뮬레이션', 6900, 69000, 5, 20, true),
            ('STANDARD', '스탠다드', 29000, 290000, 10, 50, true),
            ('PRO', '프로', 59000, 590000, NULL, NULL, true);
        """
        conn.execute(text(plans_sql))
        conn.commit()
        print("  - New plans created:")
        print("    * SIMULATION: 6,900원/월 (시뮬레이터 전용)")
        print("    * STANDARD: 29,000원/월")
        print("    * PRO: 59,000원/월")
        
        print("\n[Step 3/3] Creating commission rates...")
        
        # Commission rates
        rates_sql = """
        INSERT INTO commission_rates (plan_id, event_type, rate_percentage, is_active, description)
        SELECT 
            sp.id,
            'SIGNUP',
            CASE 
                WHEN sp.name = 'SIMULATION' THEN 5.0
                WHEN sp.name = 'STANDARD' THEN 10.0
                WHEN sp.name = 'PRO' THEN 15.0
            END,
            true,
            CASE 
                WHEN sp.name = 'SIMULATION' THEN '시뮬레이션 플랜 가입 커미션 5%'
                WHEN sp.name = 'STANDARD' THEN '스탠다드 플랜 가입 커미션 10%'
                WHEN sp.name = 'PRO' THEN '프로 플랜 가입 커미션 15%'
            END
        FROM subscription_plans sp
        WHERE sp.name IN ('SIMULATION', 'STANDARD', 'PRO');
        """
        conn.execute(text(rates_sql))
        conn.commit()
        print("  - Commission rates created")
        
        print("\n[Plan Update] ✅ Successfully updated subscription plans!")
        print("\nNew Plan Structure:")
        print("  1. SIMULATION (6,900원/월)")
        print("     - Broker: Simulator only")
        print("     - Max conditions: 5")
        print("     - Max stocks: 20")
        print("  2. STANDARD (29,000원/월)")
        print("     - Broker: All brokers")
        print("     - Max conditions: 10")
        print("     - Max stocks: 50")
        print("  3. PRO (59,000원/월)")
        print("     - Broker: All brokers")
        print("     - Max conditions: Unlimited")
        print("     - Max stocks: Unlimited")
        
except Exception as e:
    print(f"\n[Plan Update] Error: {e}")
    raise
