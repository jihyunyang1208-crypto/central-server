"""
Quick Update Script for Gemini API Key
Run this script with your new API key as an argument
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.system_config import SystemConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_api_key(new_api_key: str):
    """
    Update Gemini API key in database
    
    Args:
        new_api_key: New Gemini API key from Google AI Studio
    """
    if not new_api_key or len(new_api_key) < 20:
        logger.error("❌ Invalid API key. Please provide a valid Gemini API key.")
        return False
    
    db: Session = SessionLocal()
    
    try:
        # Update API key
        api_key_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_api_key"
        ).first()
        
        if not api_key_config:
            logger.error("❌ No existing API key config found. Run save_gemini_config.py first.")
            return False
        
        config_value = {
            "api_key": new_api_key,
            "is_valid": True
        }
        
        api_key_config.config_value = config_value
        api_key_config.updated_by = "admin_quick_update"
        
        db.commit()
        
        # Mask the key for display
        masked_key = ""
        if len(new_api_key) > 14:
            masked_key = new_api_key[:10] + "..." + new_api_key[-4:]
        else:
            masked_key = new_api_key[:4] + "..."
        
        logger.info(f"✅ API key updated successfully: {masked_key}")
        logger.info("\n📋 Next steps:")
        logger.info("1. Restart AutoTrader agent: Ctrl+C then 'py agent/main.py'")
        logger.info("2. Test with: python test_gemini_centralized.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update API key: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n" + "=" * 60)
        print("Quick Gemini API Key Update")
        print("=" * 60)
        print("\nUsage:")
        print("  python update_gemini_key.py YOUR_NEW_API_KEY")
        print("\nExample:")
        print("  python update_gemini_key.py AIzaSyABC123...")
        print("\nGet your API key from:")
        print("  https://aistudio.google.com/app/apikey")
        print("=" * 60)
        sys.exit(1)
    
    new_key = sys.argv[1]
    
    logger.info("=" * 60)
    logger.info("Updating Gemini API Key")
    logger.info("=" * 60)
    
    init_db()
    success = update_api_key(new_key)
    
    sys.exit(0 if success else 1)
