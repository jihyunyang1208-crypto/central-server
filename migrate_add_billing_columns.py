# migrate_add_billing_columns.py
"""
Add billing-related columns to subscriptions table
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Adding billing columns to subscriptions table...")
        
        # Add all billing columns
        conn.execute(text("""
            ALTER TABLE subscriptions 
            ADD COLUMN IF NOT EXISTS billing_key VARCHAR,
            ADD COLUMN IF NOT EXISTS billing_period VARCHAR DEFAULT 'monthly',
            ADD COLUMN IF NOT EXISTS card_last4 VARCHAR(4),
            ADD COLUMN IF NOT EXISTS card_company VARCHAR,
            ADD COLUMN IF NOT EXISTS last_payment_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS next_payment_date TIMESTAMP
        """))
        
        # Create index on billing_key and next_payment_date
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_billing_key 
            ON subscriptions(billing_key)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_next_payment 
            ON subscriptions(next_payment_date)
        """))
        
        conn.commit()
        print("[OK] Migration completed successfully!")
        print("Added columns: billing_key, billing_period, card_last4, card_company, last_payment_at, next_payment_date")
        print("Created indexes on billing_key and next_payment_date")

if __name__ == "__main__":
    migrate()
