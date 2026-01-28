"""
Update Gemini models to latest versions (2026)
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.models.system_config import SystemConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_to_latest_models():
    """Update Gemini model priority to latest versions"""
    db: Session = SessionLocal()
    
    try:
        # Latest model priority (2026-01)
        latest_models = {
            "preferred_models": [
                "gemini-2.5-flash",      # Best balance of speed and performance
                "gemini-2.5-pro",        # Complex reasoning backup
                "gemini-3-flash"         # Latest features (if needed)
            ],
            "fallback_model": "gemini-2.5-flash"
        }
        
        # Update models config
        models_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_models"
        ).first()
        
        if models_config:
            logger.info("Updating existing Gemini models config...")
            old_models = models_config.config_value.get("preferred_models", [])
            logger.info(f"  Old models: {old_models}")
            
            models_config.config_value = latest_models
            models_config.updated_by = "system_update_2026"
        else:
            logger.info("Creating new Gemini models config...")
            models_config = SystemConfig(
                config_key="gemini_models",
                config_value=latest_models,
                description="Gemini AI model priority list (Updated 2026-01)",
                updated_by="system_update_2026"
            )
            db.add(models_config)
        
        db.commit()
        
        logger.info(f"  New models: {latest_models['preferred_models']}")
        logger.info(f"  Fallback: {latest_models['fallback_model']}")
        logger.info("\n✅ Models updated successfully!")
        logger.info("\n📋 Next steps:")
        logger.info("1. Restart AutoTrader agent to use new models")
        logger.info("2. Test with: python test_gemini_centralized.py")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update models: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Updating to Latest Gemini Models (2026-01)")
    logger.info("=" * 60)
    
    init_db()
    success = update_to_latest_models()
    
    sys.exit(0 if success else 1)
