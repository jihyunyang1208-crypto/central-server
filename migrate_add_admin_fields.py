"""
Database migration: Add admin fields to users table
Adds is_admin and last_active_at columns for admin dashboard functionality
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/aut_db")

def run_migration():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Starting migration: Add admin fields...")
        
        # Add is_admin column
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
            """))
            print("✓ Added is_admin column")
        except Exception as e:
            print(f"is_admin column might already exist: {e}")
        
        # Add last_active_at column
        try:
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP;
            """))
            print("✓ Added last_active_at column")
        except Exception as e:
            print(f"last_active_at column might already exist: {e}")
        
        # Create index for performance
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_last_active 
                ON users(last_active_at);
            """))
            print("✓ Created index on last_active_at")
        except Exception as e:
            print(f"Index might already exist: {e}")
        
        # Set initial last_active_at for existing users
        try:
            conn.execute(text("""
                UPDATE users 
                SET last_active_at = created_at 
                WHERE last_active_at IS NULL;
            """))
            print("✓ Set initial last_active_at values")
        except Exception as e:
            print(f"Error setting initial values: {e}")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nTo set an admin user, run:")
        print("UPDATE users SET is_admin = true WHERE email = 'your_admin@email.com';")

if __name__ == "__main__":
    run_migration()
