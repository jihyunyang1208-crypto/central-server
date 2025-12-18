# central-backend/migrate_add_columns.py
"""
데이터베이스 마이그레이션: 누락된 컬럼 추가
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

print(f"[Migration] Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

migrations = [
    # Add is_email_verified to users table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_email_verified'
        ) THEN
            ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT FALSE;
            RAISE NOTICE 'Added column is_email_verified to users table';
        ELSE
            RAISE NOTICE 'Column is_email_verified already exists';
        END IF;
    END $$;
    """,
    
    # Add referral_code to users table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='referral_code'
        ) THEN
            ALTER TABLE users ADD COLUMN referral_code VARCHAR UNIQUE;
            RAISE NOTICE 'Added column referral_code to users table';
        ELSE
            RAISE NOTICE 'Column referral_code already exists';
        END IF;
    END $$;
    """,
    
    # Add referred_by_id to users table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='referred_by_id'
        ) THEN
            ALTER TABLE users ADD COLUMN referred_by_id INTEGER REFERENCES users(id);
            RAISE NOTICE 'Added column referred_by_id to users table';
        ELSE
            RAISE NOTICE 'Column referred_by_id already exists';
        END IF;
    END $$;
    """,
    
    # Add last_login_at to users table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='last_login_at'
        ) THEN
            ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
            RAISE NOTICE 'Added column last_login_at to users table';
        ELSE
            RAISE NOTICE 'Column last_login_at already exists';
        END IF;
    END $$;
    """,
    
    # Add created_at to users table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='created_at'
        ) THEN
            ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            RAISE NOTICE 'Added column created_at to users table';
        ELSE
            RAISE NOTICE 'Column created_at already exists';
        END IF;
    END $$;
    """,
    
    # Add updated_at to users table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='users' AND column_name='updated_at'
        ) THEN
            ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            RAISE NOTICE 'Added column updated_at to users table';
        ELSE
            RAISE NOTICE 'Column updated_at already exists';
        END IF;
    END $$;
    """,
    
    # Add buy_condition_formulas to trading_settings table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='trading_settings' AND column_name='buy_condition_formulas'
        ) THEN
            ALTER TABLE trading_settings ADD COLUMN buy_condition_formulas JSON DEFAULT '[]';
            RAISE NOTICE 'Added column buy_condition_formulas to trading_settings table';
        ELSE
            RAISE NOTICE 'Column buy_condition_formulas already exists';
        END IF;
    END $$;
    """,
    
    # Add sell_condition_formulas to trading_settings table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='trading_settings' AND column_name='sell_condition_formulas'
        ) THEN
            ALTER TABLE trading_settings ADD COLUMN sell_condition_formulas JSON DEFAULT '[]';
            RAISE NOTICE 'Added column sell_condition_formulas to trading_settings table';
        ELSE
            RAISE NOTICE 'Column sell_condition_formulas already exists';
        END IF;
    END $$;
    """,
]

try:
    with engine.connect() as conn:
        for i, migration in enumerate(migrations, 1):
            print(f"\n[Migration {i}/{len(migrations)}] Executing...")
            result = conn.execute(text(migration))
            conn.commit()
            print(f"[Migration {i}] Success")
    
    print("\n[Migration] All migrations completed successfully!")
    
except Exception as e:
    print(f"\n[Migration] Error: {e}")
    raise
