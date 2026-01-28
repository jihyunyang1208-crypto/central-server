# central-backend/app/services/data_collector.py
"""
재무 데이터 수집 서비스
- OpenDartReader: 재무제표 수집
- FinanceDataReader: 일봉 데이터 수집
- Naver 크롤링: Fallback
"""
import os
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import time

# pandas import (필수)
try:
    import pandas as pd
except ImportError:
    raise ImportError("pandas is required for data collection. Install with: pip install pandas>=2.0.0")

# Data collection libraries
try:
    import OpenDartReader
    import FinanceDataReader as fdr
    from bs4 import BeautifulSoup
    import requests
except ImportError as e:
    logging.warning(f"Data collection libraries not installed: {e}")

from app.models.financial_data import (
    StockInfo, DailyPrice, FinancialStatement, 
    Disclosure, DataCollectionLog
)

logger = logging.getLogger(__name__)


class DataCollector:
    """재무 데이터 수집 메인 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.dart_api_key = os.getenv("DART_API_KEY")
        self.dart = None
        
        if self.dart_api_key:
            try:
                self.dart = OpenDartReader.OpenDartReader(self.dart_api_key)
                logger.info("✅ OpenDartReader initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenDartReader: {e}")
    
    # ============================================
    # 종목 리스트 수집
    # ============================================
    
    def collect_stock_list(self, market: Optional[str] = None) -> Tuple[int, int, int]:
        """
        KRX 상장 종목 리스트 수집
        
        Args:
            market: 시장 구분 (KOSPI/KOSDAQ/ALL)
            
        Returns:
            (total_count, success_count, failed_count)
        """
        logger.info(f"📊 Starting stock list collection (market={market})...")
        
        total_count = 0
        success_count = 0
        failed_count = 0
        
        try:
            # FinanceDataReader로 전체 종목 리스트 가져오기
            if market == "KOSPI":
                df_stocks = fdr.StockListing('KOSPI')
            elif market == "KOSDAQ":
                df_stocks = fdr.StockListing('KOSDAQ')
            else:
                # 전체 (KOSPI + KOSDAQ)
                df_kospi = fdr.StockListing('KOSPI')
                df_kosdaq = fdr.StockListing('KOSDAQ')
                df_stocks = pd.concat([df_kospi, df_kosdaq], ignore_index=True)
            
            total_count = len(df_stocks)
            logger.info(f"   Found {total_count} stocks")
            
            # DB에 배치 저장 (성능 개선)
            batch_size = 100
            for idx, (_, row) in enumerate(df_stocks.iterrows()):
                try:
                    code = row.get('Code', row.get('Symbol', ''))
                    if not code or len(code) != 6:
                        continue
                    
                    # 기존 종목 확인
                    stock = self.db.query(StockInfo).filter(StockInfo.code == code).first()
                    
                    if stock:
                        # 업데이트
                        stock.name = row.get('Name', stock.name)
                        stock.market = row.get('Market', stock.market)
                        stock.sector = row.get('Sector', row.get('Industry', stock.sector))
                        stock.updated_at = datetime.utcnow()
                    else:
                        # 신규 생성
                        stock = StockInfo(
                            code=code,
                            name=row.get('Name', ''),
                            market=row.get('Market', ''),
                            sector=row.get('Sector', row.get('Industry', '')),
                            is_active=True,
                            listed_date=row.get('ListingDate', None)
                        )
                        self.db.add(stock)
                    
                    success_count += 1
                    
                    # 배치 커밋 (100개마다)
                    if (idx + 1) % batch_size == 0:
                        self.db.commit()
                        logger.info(f"   Progress: {success_count}/{total_count}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to save stock {code}: {e}", exc_info=True)
                    self.db.rollback()
                    failed_count += 1
            
            # 최종 커밋
            self.db.commit()
            
            # 메모리 정리
            del df_stocks
            if 'df_kospi' in locals():
                del df_kospi
            if 'df_kosdaq' in locals():
                del df_kosdaq
            
            logger.info(f"✅ Stock list collection completed: {success_count}/{total_count} succeeded")
            
        except Exception as e:
            logger.error(f"❌ Stock list collection failed: {e}")
            failed_count = total_count
        
        return total_count, success_count, failed_count
    
    # ============================================
    # 일봉 데이터 수집
    # ============================================
    
    def collect_daily_prices(
        self, 
        code: str, 
        start_date: date, 
        end_date: date
    ) -> Tuple[int, int, int]:
        """
        일봉 데이터 수집 및 이동평균선 계산
        
        Args:
            code: 종목코드
            start_date: 시작일
            end_date: 종료일
            
        Returns:
            (total_count, success_count, failed_count)
        """
        logger.info(f"📈 Collecting daily prices for {code} ({start_date} ~ {end_date})...")
        
        total_count = 0
        success_count = 0
        failed_count = 0
        
        try:
            # FinanceDataReader로 일봉 데이터 가져오기
            df = fdr.DataReader(code, start_date, end_date)
            
            if df is None or df.empty:
                logger.warning(f"   No data found for {code}")
                return 0, 0, 0
            
            total_count = len(df)
            
            # 이동평균선 계산
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['MA120'] = df['Close'].rolling(window=120).mean()
            df['MA180'] = df['Close'].rolling(window=180).mean()
            
            # 전일대비 계산
            df['Change'] = df['Close'].diff()
            df['ChangePercent'] = (df['Change'] / df['Close'].shift(1)) * 100
            
            # DB에 저장
            for date_idx, row in df.iterrows():
                try:
                    trade_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                    
                    # 기존 데이터 확인 (upsert)
                    daily_price = self.db.query(DailyPrice).filter(
                        and_(DailyPrice.code == code, DailyPrice.date == trade_date)
                    ).first()
                    
                    if daily_price:
                        # 업데이트
                        daily_price.open = float(row['Open'])
                        daily_price.high = float(row['High'])
                        daily_price.low = float(row['Low'])
                        daily_price.close = float(row['Close'])
                        daily_price.volume = int(row['Volume'])
                        daily_price.change = float(row['Change']) if pd.notna(row['Change']) else None
                        daily_price.change_percent = float(row['ChangePercent']) if pd.notna(row['ChangePercent']) else None
                        daily_price.ma5 = float(row['MA5']) if pd.notna(row['MA5']) else None
                        daily_price.ma10 = float(row['MA10']) if pd.notna(row['MA10']) else None
                        daily_price.ma20 = float(row['MA20']) if pd.notna(row['MA20']) else None
                        daily_price.ma60 = float(row['MA60']) if pd.notna(row['MA60']) else None
                        daily_price.ma120 = float(row['MA120']) if pd.notna(row['MA120']) else None
                        daily_price.ma180 = float(row['MA180']) if pd.notna(row['MA180']) else None
                        daily_price.updated_at = datetime.utcnow()
                    else:
                        # 신규 생성
                        daily_price = DailyPrice(
                            code=code,
                            date=trade_date,
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            close=float(row['Close']),
                            volume=int(row['Volume']),
                            change=float(row['Change']) if pd.notna(row['Change']) else None,
                            change_percent=float(row['ChangePercent']) if pd.notna(row['ChangePercent']) else None,
                            ma5=float(row['MA5']) if pd.notna(row['MA5']) else None,
                            ma10=float(row['MA10']) if pd.notna(row['MA10']) else None,
                            ma20=float(row['MA20']) if pd.notna(row['MA20']) else None,
                            ma60=float(row['MA60']) if pd.notna(row['MA60']) else None,
                            ma120=float(row['MA120']) if pd.notna(row['MA120']) else None,
                            ma180=float(row['MA180']) if pd.notna(row['MA180']) else None,
                        )
                        self.db.add(daily_price)
                    
                    success_count += 1
                    
                    # 배치 커밋 (100개마다)
                    if success_count % 100 == 0:
                        self.db.commit()
                        logger.info(f"   Progress: {success_count}/{total_count}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to save daily price for {code} on {trade_date}: {e}")
                    self.db.rollback()
                    failed_count += 1
            
            # 최종 커밋
            self.db.commit()
            logger.info(f"✅ Daily prices collection completed: {success_count}/{total_count} succeeded")
            
            # 메모리 정리
            del df
            
        except Exception as e:
            logger.error(f"❌ Daily prices collection failed for {code}: {e}", exc_info=True)
            self.db.rollback()
            failed_count = total_count
        
        return total_count, success_count, failed_count
    
    # ============================================
    # 재무제표 수집
    # ============================================
    
    def collect_financial_statements(
        self, 
        code: str, 
        year: int, 
        quarter: Optional[int] = None
    ) -> Tuple[int, int, int]:
        """
        재무제표 수집 (OpenDartReader 사용)
        
        Args:
            code: 종목코드
            year: 회계연도
            quarter: 분기 (1~4, None이면 연간)
            
        Returns:
            (total_count, success_count, failed_count)
        """
        if not self.dart:
            logger.error("❌ OpenDartReader not initialized")
            return 0, 0, 1
        
        logger.info(f"📊 Collecting financial statements for {code} ({year}Q{quarter or 'Annual'})...")
        
        total_count = 1
        success_count = 0
        failed_count = 0
        
        try:
            # DART에서 재무제표 가져오기
            # 분기보고서 또는 사업보고서
            report_type = '11013' if quarter else '11011'  # 11013: 분기보고서, 11011: 사업보고서
            
            # 재무제표 조회
            df_fs = self.dart.finstate(code, year, reprt_code=report_type)
            
            if df_fs is None or df_fs.empty:
                logger.warning(f"   No financial data found for {code}")
                return 0, 0, 0
            
            # 재무 데이터 파싱 및 저장
            financial_data = self._parse_financial_statement(df_fs)
            
            if not financial_data:
                logger.warning(f"   Failed to parse financial data for {code}")
                return total_count, 0, 1
            
            # DB에 저장 (upsert)
            fs = self.db.query(FinancialStatement).filter(
                and_(
                    FinancialStatement.code == code,
                    FinancialStatement.year == year,
                    FinancialStatement.quarter == (quarter or 0)
                )
            ).first()
            
            if fs:
                # 업데이트
                for key, value in financial_data.items():
                    setattr(fs, key, value)
                fs.updated_at = datetime.utcnow()
            else:
                # 신규 생성
                fs = FinancialStatement(
                    code=code,
                    year=year,
                    quarter=quarter or 0,
                    source="DART",
                    **financial_data
                )
                self.db.add(fs)
            
            self.db.commit()
            success_count = 1
            
            # StockInfo의 최신 재무 데이터 업데이트
            self._update_stock_latest_financial(code, year, quarter or 0, financial_data)
            
            logger.info(f"✅ Financial statement collected successfully")
            
        except Exception as e:
            logger.error(f"❌ Financial statement collection failed for {code}: {e}", exc_info=True)
            self.db.rollback()
            failed_count = 1
        
        return total_count, success_count, failed_count
    
    def _parse_financial_statement(self, df: 'pd.DataFrame') -> Dict:
        """재무제표 데이터 파싱"""
        try:
            data = {}
            
            # 주요 계정과목 매핑
            account_mapping = {
                '매출액': 'revenue',
                '영업이익': 'operating_profit',
                '당기순이익': 'net_profit',
                '자산총계': 'total_assets',
                '부채총계': 'total_liabilities',
                '자본총계': 'total_equity',
                '영업활동현금흐름': 'operating_cash_flow',
                '투자활동현금흐름': 'investing_cash_flow',
                '재무활동현금흐름': 'financing_cash_flow',
            }
            
            for account_name, field_name in account_mapping.items():
                value = self._extract_account_value(df, account_name)
                if value is not None:
                    # 억원 단위로 변환
                    data[field_name] = value / 100000000
            
            # 재무비율 계산
            if 'revenue' in data and 'operating_profit' in data and data['revenue'] > 0:
                data['operating_margin'] = (data['operating_profit'] / data['revenue']) * 100
            
            if 'revenue' in data and 'net_profit' in data and data['revenue'] > 0:
                data['net_margin'] = (data['net_profit'] / data['revenue']) * 100
            
            if 'total_equity' in data and 'net_profit' in data and data['total_equity'] > 0:
                data['roe'] = (data['net_profit'] / data['total_equity']) * 100
            
            if 'total_assets' in data and 'net_profit' in data and data['total_assets'] > 0:
                data['roa'] = (data['net_profit'] / data['total_assets']) * 100
            
            if 'total_liabilities' in data and 'total_equity' in data and data['total_equity'] > 0:
                data['debt_ratio'] = (data['total_liabilities'] / data['total_equity']) * 100
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to parse financial statement: {e}", exc_info=True)
            return {}
    
    def _extract_account_value(self, df: 'pd.DataFrame', account_name: str) -> Optional[float]:
        """재무제표에서 특정 계정과목 값 추출"""
        try:
            # 계정명으로 필터링
            filtered = df[df['account_nm'].str.contains(account_name, na=False)]
            if not filtered.empty:
                # 당기 금액 추출
                value_str = filtered.iloc[0].get('thstrm_amount', '0')
                return float(value_str.replace(',', ''))
            return None
        except Exception:
            return None
    
    def _update_stock_latest_financial(
        self, 
        code: str, 
        year: int, 
        quarter: int, 
        financial_data: Dict
    ):
        """StockInfo의 최신 재무 데이터 업데이트"""
        try:
            stock = self.db.query(StockInfo).filter(StockInfo.code == code).first()
            if stock:
                stock.latest_revenue = financial_data.get('revenue')
                stock.latest_operating_profit = financial_data.get('operating_profit')
                stock.latest_operating_margin = financial_data.get('operating_margin')
                stock.latest_net_profit = financial_data.get('net_profit')
                stock.latest_debt_ratio = financial_data.get('debt_ratio')
                stock.latest_roe = financial_data.get('roe')
                stock.latest_financial_year = year
                stock.latest_financial_quarter = quarter
                stock.latest_financial_updated_at = datetime.utcnow()
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update stock latest financial: {e}", exc_info=True)
            self.db.rollback()
    
    # ============================================
    # 로그 기록
    # ============================================
    
    def create_collection_log(
        self,
        collection_type: str,
        status: str,
        total_count: int,
        success_count: int,
        failed_count: int,
        error_message: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> int:
        """데이터 수집 로그 생성"""
        try:
            log = DataCollectionLog(
                collection_type=collection_type,
                status=status,
                total_count=total_count,
                success_count=success_count,
                failed_count=failed_count,
                error_message=error_message,
                start_date=start_date,
                end_date=end_date,
                started_at=started_at or datetime.utcnow(),
                completed_at=completed_at
            )
            self.db.add(log)
            self.db.commit()
            return log.id
        except Exception as e:
            logger.error(f"Failed to create collection log: {e}", exc_info=True)
            self.db.rollback()
            return 0
