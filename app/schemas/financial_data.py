# central-backend/app/schemas/financial_data.py
"""
재무 데이터 API 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ============================================
# Request Schemas
# ============================================

class CollectStocksRequest(BaseModel):
    """종목 리스트 수집 요청"""
    market: Optional[str] = Field(None, description="시장 구분 (KOSPI/KOSDAQ/ALL)")


class CollectDailyPricesRequest(BaseModel):
    """일봉 데이터 수집 요청"""
    code: Optional[str] = Field(None, description="종목코드 (없으면 전체)")
    start_date: date = Field(..., description="시작일")
    end_date: date = Field(..., description="종료일")


class CollectFinancialStatementsRequest(BaseModel):
    """재무제표 수집 요청"""
    code: Optional[str] = Field(None, description="종목코드 (없으면 전체)")
    year: int = Field(..., description="회계연도")
    quarter: Optional[int] = Field(None, description="분기 (1~4, 없으면 연간)")


# ============================================
# Response Schemas
# ============================================

class StockInfoResponse(BaseModel):
    """종목 정보 응답"""
    id: int
    code: str
    name: str
    market: Optional[str]
    sector: Optional[str]
    is_active: bool
    latest_market_cap: Optional[float]
    latest_operating_margin: Optional[float]
    latest_debt_ratio: Optional[float]
    
    class Config:
        from_attributes = True


class DailyPriceResponse(BaseModel):
    """일봉 데이터 응답"""
    id: int
    code: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    change: Optional[float]
    change_percent: Optional[float]
    ma5: Optional[float]
    ma10: Optional[float]
    ma20: Optional[float]
    ma60: Optional[float]
    ma120: Optional[float]
    ma180: Optional[float]
    
    class Config:
        from_attributes = True


class FinancialStatementResponse(BaseModel):
    """재무제표 응답"""
    id: int
    code: str
    year: int
    quarter: int
    revenue: Optional[float]
    operating_profit: Optional[float]
    net_profit: Optional[float]
    operating_margin: Optional[float]
    net_margin: Optional[float]
    roe: Optional[float]
    roa: Optional[float]
    total_assets: Optional[float]
    total_liabilities: Optional[float]
    total_equity: Optional[float]
    debt_ratio: Optional[float]
    market_cap: Optional[float]
    source: Optional[str]
    
    class Config:
        from_attributes = True


class DataCollectionLogResponse(BaseModel):
    """데이터 수집 로그 응답"""
    id: int
    collection_type: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    error_message: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    started_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CollectionResponse(BaseModel):
    """수집 작업 응답"""
    success: bool
    message: str
    log_id: Optional[int] = None
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0


class StockListResponse(BaseModel):
    """종목 리스트 응답"""
    total: int
    stocks: List[StockInfoResponse]


class DailyPriceListResponse(BaseModel):
    """일봉 데이터 리스트 응답"""
    code: str
    total: int
    prices: List[DailyPriceResponse]


class FinancialStatementListResponse(BaseModel):
    """재무제표 리스트 응답"""
    code: str
    total: int
    statements: List[FinancialStatementResponse]
