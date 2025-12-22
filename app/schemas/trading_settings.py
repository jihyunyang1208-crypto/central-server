# central-backend/app/schemas/trading_settings.py
"""
트레이딩 설정 Pydantic 스키마
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class StandardBuyConfig(BaseModel):
    """Standard 플랜 매수 설정"""
    order_type: str = Field(default="limit", description="주문 타입: limit | market")
    unit_amount: int = Field(default=100000, ge=10000, description="단위 금액")
    num_slices: int = Field(default=10, ge=1, le=20, description="분할 개수")
    start_ticks_below: int = Field(default=1, ge=0, description="시작 틱 아래")
    step_ticks: int = Field(default=1, ge=1, description="단계 틱")


class ProBuyConfig(BaseModel):
    """Pro 플랜 매수 설정"""
    check_5m: bool = Field(default=True, description="5분봉 체크")
    check_30m: bool = Field(default=False, description="30분봉 체크")
    check_1d: bool = Field(default=False, description="일봉 체크")
    use_macd30_filter: bool = Field(default=False, description="MACD 30분 필터 사용")
    allow_intrabar_triggers: bool = Field(default=True, description="봉 내 트리거 허용")
    indicators: Dict[str, Any] = Field(default={
        "rsi_enabled": False,
        "rsi_threshold": 70,
        "macd_enabled": False
    })


class StandardSellConfig(BaseModel):
    """Standard 플랜 매도 설정"""
    profit_threshold: float = Field(default=0.03, ge=0, le=1, description="익절 비율")
    loss_threshold: float = Field(default=-0.015, ge=-1, le=0, description="손절 비율")
    time_limit_hours: int = Field(default=24, ge=1, description="보유 시간 제한(시간)")
    enable_stoploss: bool = Field(default=False, description="손절 활성화")


class ProSellConfig(BaseModel):
    """Pro 플랜 매도 설정"""
    use_trend_reversal: bool = Field(default=True, description="추세 전환 사용")
    condition_formula_ids: List[str] = Field(default=[], description="조건식 IDs")
    partial_exit_enabled: bool = Field(default=False, description="분할 청산 활성화")
    partial_exit_ratios: List[float] = Field(default=[0.5, 0.5], description="분할 청산 비율")


class TrailingStopConfig(BaseModel):
    """트레일링 스탑 설정"""
    enabled: bool = Field(default=False, description="사용 여부")
    trailing_percent: float = Field(default=0.05, ge=0.001, le=1.0, description="트레일링 간격 (예: 0.05 = 5%)")
    activation_profit: float = Field(default=0.03, ge=0.0, description="활성화 수익률 (예: 0.03 = 3%)")
    min_profit_lock: float = Field(default=0.01, ge=0.0, description="최소 보전 수익률")
    timeframe: str = Field(default="5m", description="감시 타임프레임")



class TradingSettingsBase(BaseModel):
    """트레이딩 설정 기본"""
    auto_buy: bool = True
    auto_sell: bool = False
    buy_mode: str = Field(default="STANDARD", pattern="^(STANDARD|PRO)$")
    sell_mode: str = Field(default="STANDARD", pattern="^(STANDARD|PRO)$")
    standard_buy_config: Optional[StandardBuyConfig] = None
    pro_buy_config: Optional[ProBuyConfig] = None
    standard_sell_config: Optional[StandardSellConfig] = None
    pro_sell_config: Optional[ProSellConfig] = None
    trailing_stop_config: Optional[TrailingStopConfig] = None
    max_active_strategies: int = Field(default=5, ge=1, le=100)
    max_active_strategies: int = Field(default=5, ge=1, le=100)
    buy_condition_formulas: List[str] = Field(default=[], description="매수 전용 조건검색식 ID 리스트")
    sell_condition_formulas: List[str] = Field(default=[], description="매도 전용 조건검색식 ID 리스트")


class TradingSettingsCreate(TradingSettingsBase):
    """트레이딩 설정 생성"""
    pass


class TradingSettingsUpdate(BaseModel):
    """트레이딩 설정 업데이트 (부분 업데이트 허용)"""
    auto_buy: Optional[bool] = None
    auto_sell: Optional[bool] = None
    buy_mode: Optional[str] = Field(None, pattern="^(STANDARD|PRO)$")
    sell_mode: Optional[str] = Field(None, pattern="^(STANDARD|PRO)$")
    standard_buy_config: Optional[Dict[str, Any]] = None
    pro_buy_config: Optional[Dict[str, Any]] = None
    standard_sell_config: Optional[Dict[str, Any]] = None
    pro_sell_config: Optional[Dict[str, Any]] = None
    trailing_stop_config: Optional[Dict[str, Any]] = None
    max_active_strategies: Optional[int] = Field(None, ge=1, le=100)
    max_active_strategies: Optional[int] = Field(None, ge=1, le=100)
    buy_condition_formulas: Optional[List[str]] = Field(None, description="매수 전용 조건검색식 ID 리스트")
    sell_condition_formulas: Optional[List[str]] = Field(None, description="매도 전용 조건검색식 ID 리스트")


class TradingSettingsResponse(TradingSettingsBase):
    """트레이딩 설정 응답"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
