"""
Add created_at and updated_at columns to system_configs table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import SessionLocal, init_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add timestamp columns to system_configs table"""
    db = SessionLocal()
    
    try:
        logger.info("Checking system_configs table structure...")
        
        # Check if columns already exist
        result = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'system_configs' AND column_name IN ('created_at', 'updated_at')"
        ))
        existing_columns = [row[0] for row in result]
        
        if 'created_at' in existing_columns and 'updated_at' in existing_columns:
            logger.info("✅ Columns already exist, no migration needed")
            return True
        
        # Add created_at column
        if 'created_at' not in existing_columns:
            logger.info("Adding created_at column...")
            db.execute(text(
                "ALTER TABLE system_configs "
                "ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            ))
            logger.info("✅ created_at column added")
        
        # Add updated_at column
        if 'updated_at' not in existing_columns:
            logger.info("Adding updated_at column...")
            db.execute(text(
                "ALTER TABLE system_configs "
                "ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"
            ))
            logger.info("✅ updated_at column added")
        
        db.commit()
        logger.info("✅ Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Migrating system_configs table")
    logger.info("=" * 60)
    
    init_db()
    success = migrate()
    
    if success:
        logger.info("\n✅ Migration completed!")
    else:
        logger.error("\n❌ Migration failed")
        sys.exit(1)
