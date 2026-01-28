"""
Gemini API 키를 Central Backend DB에 저장하는 스크립트
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


def save_gemini_config(api_key: str, model_priority: list = None):
    """
    Gemini API 키와 모델 우선순위를 DB에 저장
    
    Args:
        api_key: Gemini API 키
        model_priority: 모델 우선순위 리스트 (기본값: ["gemini-1.5-flash"])
    """
    if model_priority is None:
        model_priority = ["gemini-1.5-flash"]
    
    db: Session = SessionLocal()
    
    try:
        # 1. API 키 저장
        api_key_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_api_key"
        ).first()
        
        config_value = {
            "api_key": api_key,
            "is_valid": True
        }
        
        if api_key_config:
            logger.info("Updating existing Gemini API key...")
            api_key_config.config_value = config_value
            api_key_config.updated_by = "system_admin"
        else:
            logger.info("Creating new Gemini API key config...")
            api_key_config = SystemConfig(
                config_key="gemini_api_key",
                config_value=config_value,
                description="Gemini AI API Key",
                updated_by="system_admin"
            )
            db.add(api_key_config)
        
        # 2. 모델 우선순위 저장
        models_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_models"
        ).first()
        
        models_value = {
            "preferred_models": model_priority,
            "fallback_model": model_priority[0] if model_priority else "gemini-1.5-flash"
        }
        
        if models_config:
            logger.info("Updating existing Gemini models config...")
            models_config.config_value = models_value
            models_config.updated_by = "system_admin"
        else:
            logger.info("Creating new Gemini models config...")
            models_config = SystemConfig(
                config_key="gemini_models",
                config_value=models_value,
                description="Gemini AI model priority list",
                updated_by="system_admin"
            )
            db.add(models_config)
        
        db.commit()
        
        # 마스킹된 키 표시
        masked_key = ""
        if api_key:
            if len(api_key) > 14:
                masked_key = api_key[:10] + "..." + api_key[-4:]
            else:
                masked_key = api_key[:4] + "..."
        
        logger.info(f"✅ Gemini API key saved: {masked_key}")
        logger.info(f"✅ Model priority saved: {model_priority}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save Gemini config: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # 데이터베이스 초기화
    init_db()
    
    # 새 API 키 설정
    NEW_API_KEY = "AIzaSyAZmw8_gNu7m20OZrfm5xWa9e17gSBSL_8"
    MODEL_PRIORITY = ["gemini-1.5-flash", "gemini-1.5-pro"]
    
    logger.info("=" * 60)
    logger.info("Saving Gemini API configuration to Central Backend DB")
    logger.info("=" * 60)
    
    success = save_gemini_config(NEW_API_KEY, MODEL_PRIORITY)
    
    if success:
        logger.info("\n✅ Configuration saved successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Restart AutoTrader agent to use new API key")
        logger.info("2. Remove GEMINI_API_KEY from AutoTrader .env file (optional)")
    else:
        logger.error("\n❌ Failed to save configuration")
        sys.exit(1)
