# central-backend/app/routers/financial_data.py
"""
재무 데이터 API 라우터
백테스팅을 위한 데이터 수집 및 조회 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date

from app.core.database import get_db
from app.services.data_collector import DataCollector
from app.services.stock_service import StockService
from app.services.data_scheduler import get_scheduler
from app.schemas.financial_data import (
    CollectStocksRequest,
    CollectDailyPricesRequest,
    CollectFinancialStatementsRequest,
    CollectionResponse,
    StockListResponse,
    StockInfoResponse,
    DailyPriceListResponse,
    DailyPriceResponse,
    FinancialStatementListResponse,
    FinancialStatementResponse,
    DataCollectionLogResponse
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/financial", tags=["Financial Data"])


# ============================================
# 스케줄러 관리 API
# ============================================

@router.post("/scheduler/trigger/daily-prices")
async def trigger_daily_prices_update(background_tasks: BackgroundTasks):
    """
    일봉 데이터 수집 즉시 실행 (수동 트리거)
    
    - 백그라운드에서 실행되므로 즉시 응답 반환
    - 진행상황은 collection-logs API로 확인
    """
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.run_now_daily_prices)
    
    return {
        "success": True,
        "message": "Daily prices update triggered in background"
    }


@router.post("/scheduler/trigger/financial-statements")
async def trigger_financial_statements_update(background_tasks: BackgroundTasks):
    """
    재무제표 수집 즉시 실행 (수동 트리거)
    
    - 백그라운드에서 실행되므로 즉시 응답 반환
    - 진행상황은 collection-logs API로 확인
    """
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.run_now_financial_statements)
    
    return {
        "success": True,
        "message": "Financial statements update triggered in background"
    }


# ============================================
# 데이터 수집 API
# ============================================

@router.post("/collect/stocks", response_model=CollectionResponse)
async def collect_stocks(
    request: CollectStocksRequest,
    db: Session = Depends(get_db)
):
    """
    종목 리스트 수집
    
    - KRX에서 상장 종목 정보를 수집합니다
    - market: KOSPI, KOSDAQ, 또는 ALL (전체)
    """
    logger.info(f"📊 Collecting stocks (market={request.market})...")
    
    collector = DataCollector(db)
    started_at = datetime.utcnow()
    
    try:
        total, success, failed = collector.collect_stock_list(request.market)
        
        status = "success" if failed == 0 else ("partial" if success > 0 else "failed")
        
        # 로그 기록
        log_id = collector.create_collection_log(
            collection_type="stock_list",
            status=status,
            total_count=total,
            success_count=success,
            failed_count=failed,
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
        
        return CollectionResponse(
            success=status != "failed",
            message=f"Stock list collection completed: {success}/{total} succeeded",
            log_id=log_id,
            total_count=total,
            success_count=success,
            failed_count=failed
        )
        
    except Exception as e:
        logger.error(f"❌ Stock collection failed: {e}")
        
        # 에러 로그 기록
        collector.create_collection_log(
            collection_type="stock_list",
            status="failed",
            total_count=0,
            success_count=0,
            failed_count=1,
            error_message=str(e),
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/daily-prices", response_model=CollectionResponse)
async def collect_daily_prices(
    request: CollectDailyPricesRequest,
    db: Session = Depends(get_db)
):
    """
    일봉 데이터 수집
    
    - FinanceDataReader로 OHLCV 데이터 수집
    - 이동평균선 자동 계산 (MA5, MA10, MA20, MA60, MA120, MA180)
    - code가 없으면 전체 종목 수집 (시간이 오래 걸릴 수 있음)
    """
    logger.info(f"📈 Collecting daily prices (code={request.code})...")
    
    collector = DataCollector(db)
    stock_service = StockService(db)
    started_at = datetime.utcnow()
    
    try:
        # 종목 리스트 결정
        if request.code:
            codes = [request.code]
        else:
            # 전체 종목
            stocks = stock_service.get_all_stocks(is_active=True, limit=10000)
            codes = [stock.code for stock in stocks]
        
        total_count = 0
        success_count = 0
        failed_count = 0
        
        # 각 종목별 수집
        for code in codes:
            t, s, f = collector.collect_daily_prices(code, request.start_date, request.end_date)
            total_count += t
            success_count += s
            failed_count += f
        
        status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
        
        # 로그 기록
        log_id = collector.create_collection_log(
            collection_type="daily_price",
            status=status,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            start_date=request.start_date,
            end_date=request.end_date,
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
        
        return CollectionResponse(
            success=status != "failed",
            message=f"Daily prices collection completed: {success_count}/{total_count} succeeded",
            log_id=log_id,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count
        )
        
    except Exception as e:
        logger.error(f"❌ Daily prices collection failed: {e}")
        
        collector.create_collection_log(
            collection_type="daily_price",
            status="failed",
            total_count=0,
            success_count=0,
            failed_count=1,
            error_message=str(e),
            start_date=request.start_date,
            end_date=request.end_date,
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect/financial-statements", response_model=CollectionResponse)
async def collect_financial_statements(
    request: CollectFinancialStatementsRequest,
    db: Session = Depends(get_db)
):
    """
    재무제표 수집
    
    - OpenDartReader로 DART 재무제표 수집
    - quarter가 없으면 연간 보고서, 있으면 분기 보고서
    - code가 없으면 전체 종목 수집
    """
    logger.info(f"📊 Collecting financial statements (code={request.code}, year={request.year}, quarter={request.quarter})...")
    
    collector = DataCollector(db)
    stock_service = StockService(db)
    started_at = datetime.utcnow()
    
    try:
        # 종목 리스트 결정
        if request.code:
            codes = [request.code]
        else:
            # 전체 종목
            stocks = stock_service.get_all_stocks(is_active=True, limit=10000)
            codes = [stock.code for stock in stocks]
        
        total_count = 0
        success_count = 0
        failed_count = 0
        
        # 각 종목별 수집
        for code in codes:
            t, s, f = collector.collect_financial_statements(code, request.year, request.quarter)
            total_count += t
            success_count += s
            failed_count += f
        
        status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
        
        # 로그 기록
        log_id = collector.create_collection_log(
            collection_type="financial_statement",
            status=status,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
        
        return CollectionResponse(
            success=status != "failed",
            message=f"Financial statements collection completed: {success_count}/{total_count} succeeded",
            log_id=log_id,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count
        )
        
    except Exception as e:
        logger.error(f"❌ Financial statements collection failed: {e}")
        
        collector.create_collection_log(
            collection_type="financial_statement",
            status="failed",
            total_count=0,
            success_count=0,
            failed_count=1,
            error_message=str(e),
            started_at=started_at,
            completed_at=datetime.utcnow()
        )
        
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 데이터 조회 API
# ============================================

@router.get("/stocks", response_model=StockListResponse)
async def get_stocks(
    market: Optional[str] = Query(None, description="시장 구분 (KOSPI/KOSDAQ)"),
    is_active: bool = Query(True, description="상장 여부"),
    min_market_cap: Optional[float] = Query(None, description="최소 시가총액 (억원)"),
    min_operating_margin: Optional[float] = Query(None, description="최소 영업이익률 (%)"),
    max_debt_ratio: Optional[float] = Query(None, description="최대 부채비율 (%)"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """종목 리스트 조회 (필터링 지원)"""
    stock_service = StockService(db)
    
    stocks = stock_service.get_all_stocks(
        market=market,
        is_active=is_active,
        min_market_cap=min_market_cap,
        min_operating_margin=min_operating_margin,
        max_debt_ratio=max_debt_ratio,
        limit=limit,
        offset=offset
    )
    
    return StockListResponse(
        total=len(stocks),
        stocks=[StockInfoResponse.from_orm(stock) for stock in stocks]
    )


@router.get("/daily-prices/{code}", response_model=DailyPriceListResponse)
async def get_daily_prices(
    code: str,
    start_date: Optional[date] = Query(None, description="시작일"),
    end_date: Optional[date] = Query(None, description="종료일"),
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db)
):
    """특정 종목의 일봉 데이터 조회"""
    stock_service = StockService(db)
    
    prices = stock_service.get_daily_prices(
        code=code,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return DailyPriceListResponse(
        code=code,
        total=len(prices),
        prices=[DailyPriceResponse.from_orm(price) for price in prices]
    )


@router.get("/financial-statements/{code}", response_model=FinancialStatementListResponse)
async def get_financial_statements(
    code: str,
    year: Optional[int] = Query(None, description="회계연도"),
    quarter: Optional[int] = Query(None, description="분기 (1~4)"),
    db: Session = Depends(get_db)
):
    """특정 종목의 재무제표 조회"""
    stock_service = StockService(db)
    
    statements = stock_service.get_financial_statements(
        code=code,
        year=year,
        quarter=quarter
    )
    
    return FinancialStatementListResponse(
        code=code,
        total=len(statements),
        statements=[FinancialStatementResponse.from_orm(stmt) for stmt in statements]
    )


@router.get("/collection-logs", response_model=List[DataCollectionLogResponse])
async def get_collection_logs(
    collection_type: Optional[str] = Query(None, description="수집 유형"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """데이터 수집 로그 조회"""
    stock_service = StockService(db)
    
    logs = stock_service.get_collection_logs(
        collection_type=collection_type,
        limit=limit
    )
    
    return [DataCollectionLogResponse.from_orm(log) for log in logs]
