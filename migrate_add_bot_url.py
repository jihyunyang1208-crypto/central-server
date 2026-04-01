
# central-backend/migrate_add_bot_url.py
import os
import sys
from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    """users 테이블에 bot_server_url 컬럼 추가"""
    print("Migrating: Adding bot_server_url to users table...")
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # PostgreSQL
            conn.execute(text("ALTER TABLE users ADD COLUMN bot_server_url VARCHAR(255)"))
            print("Successfully added bot_server_url column.")
            conn.commit()
        except Exception as e:
            if "already exists" in str(e):
                print("Column bot_server_url already exists.")
            else:
                print(f"Error: {e}")
                # SQLite fallback (if testing locally with SQLite)
                try:
                    conn.rollback()
                    conn.execute(text("ALTER TABLE users ADD COLUMN bot_server_url VARCHAR(255)"))
                    conn.commit()
                except Exception as sqlite_e:
                    print(f"SQLite Error: {sqlite_e}")

if __name__ == "__main__":
    # Add parent dir to path to import app settings
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    migrate()
