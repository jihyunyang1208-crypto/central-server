# central-backend/migrate_add_account_options.py
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
    # Add is_condition_linked to kiwoom_credentials table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='kiwoom_credentials' AND column_name='is_condition_linked'
        ) THEN
            ALTER TABLE kiwoom_credentials ADD COLUMN is_condition_linked BOOLEAN DEFAULT FALSE;
            RAISE NOTICE 'Added column is_condition_linked to kiwoom_credentials table';
        ELSE
            RAISE NOTICE 'Column is_condition_linked already exists';
        END IF;
    END $$;
    """,
    # Add is_report_linked to kiwoom_credentials table
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='kiwoom_credentials' AND column_name='is_report_linked'
        ) THEN
            ALTER TABLE kiwoom_credentials ADD COLUMN is_report_linked BOOLEAN DEFAULT FALSE;
            RAISE NOTICE 'Added column is_report_linked to kiwoom_credentials table';
        ELSE
            RAISE NOTICE 'Column is_report_linked already exists';
        END IF;
    END $$;
    """
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
