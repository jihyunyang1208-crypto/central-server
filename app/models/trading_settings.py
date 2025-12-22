# central-backend/app/models/trading_settings.py
"""
사용자별 트레이딩 설정 모델
- Plan-based 기능 토글 (Standard/Pro)
- Buy/Sell 전략 설정
- 플랜별 제한 관리
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class TradingSettings(Base):
    """사용자별 트레이딩 설정"""
    __tablename__ = "trading_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # 기본 설정
    auto_buy = Column(Boolean, default=True, nullable=False)
    auto_sell = Column(Boolean, default=False, nullable=False)
    
    # Plan-based 기능 모드
    buy_mode = Column(String(20), default="STANDARD", nullable=False)  # STANDARD | PRO
    sell_mode = Column(String(20), default="STANDARD", nullable=False)  # STANDARD | PRO
    
    # Standard Buy 설정
    standard_buy_config = Column(JSON, default={
        "order_type": "limit",
        "unit_amount": 100000,
        "num_slices": 10,
        "start_ticks_below": 1,
        "step_ticks": 1
    })
    
    # Pro Buy 설정
    pro_buy_config = Column(JSON, default={
        "check_5m": True,
        "check_30m": False,
        "check_1d": False,
        "use_macd30_filter": False,
        "allow_intrabar_triggers": True,
        "indicators": {
            "rsi_enabled": False,
            "rsi_threshold": 70,
            "macd_enabled": False
        }
    })
    
    # Standard Sell 설정
    standard_sell_config = Column(JSON, default={
        "profit_threshold": 0.03,
        "loss_threshold": -0.015,
        "time_limit_hours": 24,
        "enable_stoploss": False
    })
    
    # Pro Sell 설정
    pro_sell_config = Column(JSON, default={
        "use_trend_reversal": True,
        "condition_formula_ids": [],  # DEPRECATED: 매도 전용 조건식 (하위 호환)
        "partial_exit_enabled": False,
        "partial_exit_ratios": [0.5, 0.5]
    })
    
    # 트레일링 스탑 설정
    trailing_stop_config = Column(JSON, default={
        "enabled": False,
        "trailing_percent": 0.05,
        "activation_profit": 0.03,
        "min_profit_lock": 0.01,
        "timeframe": "5m"
    })
    
    # 조건검색식 분리 (매수/매도 전용)
    buy_condition_formulas = Column(JSON, default=[], comment="매수 전용 조건검색식 ID 리스트")
    sell_condition_formulas = Column(JSON, default=[], comment="매도 전용 조건검색식 ID 리스트")
    
    # 전략 제한
    max_active_strategies = Column(Integer, default=5, nullable=False)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="trading_settings")
