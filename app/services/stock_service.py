# central-backend/app/services/stock_service.py
"""
종목 정보 관리 서비스
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import date

from app.models.financial_data import StockInfo, DailyPrice, FinancialStatement
import logging

logger = logging.getLogger(__name__)


class StockService:
    """종목 정보 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_stock_by_code(self, code: str) -> Optional[StockInfo]:
        """종목코드로 종목 정보 조회"""
        return self.db.query(StockInfo).filter(StockInfo.code == code).first()
    
    def get_all_stocks(
        self, 
        market: Optional[str] = None,
        is_active: bool = True,
        min_market_cap: Optional[float] = None,
        min_operating_margin: Optional[float] = None,
        max_debt_ratio: Optional[float] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[StockInfo]:
        """
        종목 리스트 조회 (필터링 지원)
        
        Args:
            market: 시장 구분 (KOSPI/KOSDAQ)
            is_active: 상장 여부
            min_market_cap: 최소 시가총액 (억원)
            min_operating_margin: 최소 영업이익률 (%)
            max_debt_ratio: 최대 부채비율 (%)
            limit: 최대 조회 개수
            offset: 오프셋
        """
        query = self.db.query(StockInfo)
        
        # 필터 적용
        if market:
            query = query.filter(StockInfo.market == market)
        
        if is_active is not None:
            query = query.filter(StockInfo.is_active == is_active)
        
        if min_market_cap:
            query = query.filter(StockInfo.latest_market_cap >= min_market_cap)
        
        if min_operating_margin:
            query = query.filter(StockInfo.latest_operating_margin >= min_operating_margin)
        
        if max_debt_ratio:
            query = query.filter(StockInfo.latest_debt_ratio <= max_debt_ratio)
        
        # 정렬 및 페이징
        query = query.order_by(desc(StockInfo.latest_market_cap))
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_daily_prices(
        self,
        code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 500
    ) -> List[DailyPrice]:
        """
        일봉 데이터 조회
        
        Args:
            code: 종목코드
            start_date: 시작일
            end_date: 종료일
            limit: 최대 조회 개수
        """
        query = self.db.query(DailyPrice).filter(DailyPrice.code == code)
        
        if start_date:
            query = query.filter(DailyPrice.date >= start_date)
        
        if end_date:
            query = query.filter(DailyPrice.date <= end_date)
        
        query = query.order_by(desc(DailyPrice.date)).limit(limit)
        
        return query.all()
    
    def get_financial_statements(
        self,
        code: str,
        year: Optional[int] = None,
        quarter: Optional[int] = None
    ) -> List[FinancialStatement]:
        """
        재무제표 조회
        
        Args:
            code: 종목코드
            year: 회계연도
            quarter: 분기
        """
        query = self.db.query(FinancialStatement).filter(FinancialStatement.code == code)
        
        if year:
            query = query.filter(FinancialStatement.year == year)
        
        if quarter is not None:
            query = query.filter(FinancialStatement.quarter == quarter)
        
        query = query.order_by(
            desc(FinancialStatement.year),
            desc(FinancialStatement.quarter)
        )
        
        return query.all()
    
    def get_collection_logs(
        self,
        collection_type: Optional[str] = None,
        limit: int = 50
    ):
        """데이터 수집 로그 조회"""
        from app.models.financial_data import DataCollectionLog
        
        query = self.db.query(DataCollectionLog)
        
        if collection_type:
            query = query.filter(DataCollectionLog.collection_type == collection_type)
        
        query = query.order_by(desc(DataCollectionLog.started_at)).limit(limit)
        
        return query.all()
