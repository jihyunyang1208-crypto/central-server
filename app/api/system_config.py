# app/api/system_config.py
"""
시스템 설정 API
- Gemini AI 모델 우선순위 관리
- Gemini API 키 관리
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.core.security import get_admin_user
from app.models.system_config import SystemConfig
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/config", tags=["System Config"])
system_router = APIRouter(prefix="/api/v1/system", tags=["System"])


# ===== Pydantic Models =====

class GeminiModelsResponse(BaseModel):
    preferred_models: List[str]
    fallback_model: str
    updated_at: str | None = None
    updated_by: str | None = None


class GeminiModelsUpdate(BaseModel):
    preferred_models: List[str]
    fallback_model: str


class GeminiApiKeyResponse(BaseModel):
    api_key: str  # Masked for security
    is_valid: bool
    updated_at: str | None = None
    updated_by: str | None = None


class GeminiApiKeyUpdate(BaseModel):
    api_key: str


class GeminiConfigResponse(BaseModel):
    """Unified Gemini configuration for AutoTrader clients"""
    model_priority: List[str]
    api_keys: Dict[str, str]  # {model_name: api_key}


# ===== Endpoints =====

@router.get("/gemini-models", response_model=GeminiModelsResponse)
async def get_gemini_models(db: Session = Depends(get_db)):
    """
    Gemini AI 모델 우선순위 목록 조회
    - 인증 불필요 (모든 에이전트가 접근 가능)
    """
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_models"
        ).first()
        
        if not config:
            # 기본값 반환
            return GeminiModelsResponse(
                preferred_models=["gemini-3-flash", "gemini-2.5-flash"],
                fallback_model="gemini-2.5-flash",
                updated_at=None,
                updated_by=None
            )
        
        value = config.config_value
        return GeminiModelsResponse(
            preferred_models=value.get("preferred_models", ["gemini-3-flash"]),
            fallback_model=value.get("fallback_model", "gemini-2.5-flash"),
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
            updated_by=config.updated_by
        )
    except Exception as e:
        logger.error(f"Failed to get Gemini models config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration")


@router.put("/gemini-models")
async def update_gemini_models(
    update: GeminiModelsUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Gemini AI 모델 설정 업데이트
    - 관리자 전용
    """
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_models"
        ).first()
        
        config_value = {
            "preferred_models": update.preferred_models,
            "fallback_model": update.fallback_model
        }
        
        if config:
            # 기존 설정 업데이트
            config.config_value = config_value
            config.updated_by = current_user.email
        else:
            # 새 설정 생성
            config = SystemConfig(
                config_key="gemini_models",
                config_value=config_value,
                description="Gemini AI model priority list",
                updated_by=current_user.email
            )
            db.add(config)
        
        db.commit()
        db.refresh(config)
        
        logger.info(f"Gemini models config updated by {current_user.email}: {update.preferred_models}")
        
        return {
            "message": "Gemini models configuration updated successfully",
            "preferred_models": update.preferred_models,
            "fallback_model": update.fallback_model,
            "updated_at": config.updated_at.isoformat(),
            "updated_by": config.updated_by
        }
    except Exception as e:
        logger.error(f"Failed to update Gemini models config: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update configuration")


# ===== Gemini API Key Management =====

@router.get("/gemini-api-key", response_model=GeminiApiKeyResponse)
async def get_gemini_api_key(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Gemini API 키 조회 (관리자 전용)
    - 보안을 위해 마스킹된 키 반환
    """
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_api_key"
        ).first()
        
        if not config:
            return GeminiApiKeyResponse(
                api_key="",
                is_valid=False,
                updated_at=None,
                updated_by=None
            )
        
        value = config.config_value
        api_key = value.get("api_key", "")
        
        # 마스킹: 앞 10자와 뒤 4자만 표시
        masked_key = ""
        if api_key:
            if len(api_key) > 14:
                masked_key = api_key[:10] + "..." + api_key[-4:]
            else:
                masked_key = api_key[:4] + "..."
        
        return GeminiApiKeyResponse(
            api_key=masked_key,
            is_valid=value.get("is_valid", False),
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
            updated_by=config.updated_by
        )
    except Exception as e:
        logger.error(f"Failed to get Gemini API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API key")


@router.put("/gemini-api-key")
async def update_gemini_api_key(
    update: GeminiApiKeyUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Gemini API 키 업데이트 (관리자 전용)
    - 새 API 키 설정
    - 유효성 검증 (선택사항)
    """
    try:
        # TODO: API 키 유효성 검증 (genai.list_models() 호출)
        is_valid = True  # 임시로 항상 True
        
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_api_key"
        ).first()
        
        config_value = {
            "api_key": update.api_key,
            "is_valid": is_valid
        }
        
        if config:
            config.config_value = config_value
            config.updated_by = current_user.email
        else:
            config = SystemConfig(
                config_key="gemini_api_key",
                config_value=config_value,
                description="Gemini AI API Key",
                updated_by=current_user.email
            )
            db.add(config)
        
        db.commit()
        db.refresh(config)
        
        logger.info(f"Gemini API key updated by {current_user.email}")
        
        # 마스킹된 키 반환
        masked_key = ""
        if update.api_key:
            if len(update.api_key) > 14:
                masked_key = update.api_key[:10] + "..." + update.api_key[-4:]
            else:
                masked_key = update.api_key[:4] + "..."
        
        return {
            "message": "Gemini API key updated successfully",
            "api_key": masked_key,
            "is_valid": is_valid,
            "updated_at": config.updated_at.isoformat(),
            "updated_by": config.updated_by
        }
    except Exception as e:
        logger.error(f"Failed to update Gemini API key: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update API key")


# ===== Unified Gemini Config Endpoint for AutoTrader =====

@system_router.get("/gemini-config", response_model=GeminiConfigResponse)
async def get_gemini_config(db: Session = Depends(get_db)):
    """
    통합 Gemini 설정 조회 (AutoTrader 클라이언트용)
    - 인증 불필요
    - 모델 우선순위 및 API 키 반환
    """
    try:
        # 모델 우선순위 가져오기
        models_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_models"
        ).first()
        
        # API 키 가져오기
        api_key_config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "gemini_api_key"
        ).first()
        
        # 기본값
        model_priority = ["gemini-2.5-flash", "gemini-1.5-flash"]
        api_keys = {}
        
        if models_config:
            value = models_config.config_value
            preferred = value.get("preferred_models", [])
            fallback = value.get("fallback_model", "gemini-2.5-flash")
            model_priority = preferred if preferred else [fallback]
        
        if api_key_config:
            value = api_key_config.config_value
            api_key = value.get("api_key", "")
            if api_key:
                # 모든 모델에 동일한 API 키 사용
                for model in model_priority:
                    api_keys[model] = api_key
        
        logger.info(f"Gemini config requested: {len(api_keys)} API keys for {len(model_priority)} models")
        
        return GeminiConfigResponse(
            model_priority=model_priority,
            api_keys=api_keys
        )
    except Exception as e:
        logger.error(f"Failed to get unified Gemini config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve Gemini configuration")
