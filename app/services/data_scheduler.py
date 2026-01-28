# central-backend/app/services/data_scheduler.py
"""
데이터 수집 스케줄러
- 매일 오후 5시: 일봉 데이터 업데이트
- 분기별 (4월, 7월, 10월, 2월): 재무제표 업데이트
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
import logging

from app.core.database import SessionLocal
from app.services.data_collector import DataCollector
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)


class DataScheduler:
    """데이터 수집 스케줄러"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Seoul')
        self.is_running = False
    
    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        # 매일 오후 5시: 일봉 데이터 업데이트
        self.scheduler.add_job(
            func=self.update_daily_prices,
            trigger=CronTrigger(hour=17, minute=0),  # 17:00 (5 PM)
            id='daily_prices_update',
            name='일봉 데이터 업데이트',
            replace_existing=True
        )
        logger.info("✅ Scheduled: 일봉 데이터 업데이트 (매일 17:00)")
        
        # 분기별 재무제표 업데이트 (4월, 7월, 10월, 2월 1일 오후 6시)
        self.scheduler.add_job(
            func=self.update_financial_statements,
            trigger=CronTrigger(month='2,4,7,10', day=1, hour=18, minute=0),  # 분기 첫날 18:00
            id='financial_statements_update',
            name='재무제표 업데이트',
            replace_existing=True
        )
        logger.info("✅ Scheduled: 재무제표 업데이트 (2월, 4월, 7월, 10월 1일 18:00)")
        
        # 스케줄러 시작
        self.scheduler.start()
        self.is_running = True
        logger.info("🚀 Data collection scheduler started")
    
    def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("🛑 Data collection scheduler stopped")
    
    def update_daily_prices(self):
        """
        일봉 데이터 업데이트 (전체 종목)
        - 매일 오후 5시 실행
        - 전일 데이터만 수집 (효율성)
        """
        logger.info("📈 Starting scheduled daily prices update...")
        
        db: Session = SessionLocal()
        try:
            collector = DataCollector(db)
            stock_service = StockService(db)
            
            # 전체 활성 종목 조회
            stocks = stock_service.get_all_stocks(is_active=True, limit=10000)
            logger.info(f"   Found {len(stocks)} active stocks")
            
            # 전일 데이터만 수집 (효율성 개선)
            # 주말/공휴일 대비 최근 3일 범위로 수집 (실제 거래일만 저장됨)
            end_date = date.today()
            start_date = end_date - timedelta(days=3)  # 최근 3일
            
            total_count = 0
            success_count = 0
            failed_count = 0
            
            # 각 종목별 수집
            for idx, stock in enumerate(stocks):
                try:
                    t, s, f = collector.collect_daily_prices(
                        stock.code, 
                        start_date, 
                        end_date
                    )
                    total_count += t
                    success_count += s
                    failed_count += f
                    
                    # 진행상황 로그 (100개마다)
                    if (idx + 1) % 100 == 0:
                        logger.info(f"   Progress: {idx + 1}/{len(stocks)} stocks processed")
                    
                except Exception as e:
                    logger.error(f"   Failed to update {stock.code}: {e}")
                    failed_count += 1
            
            # 수집 로그 기록
            status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
            collector.create_collection_log(
                collection_type="daily_price_scheduled",
                status=status,
                total_count=total_count,
                success_count=success_count,
                failed_count=failed_count,
                start_date=start_date,
                end_date=end_date,
                started_at=datetime.now(),
                completed_at=datetime.now()
            )
            
            logger.info(f"✅ Daily prices update completed: {success_count}/{total_count} succeeded")
            
            # 1년 이상 오래된 데이터 자동 삭제
            self._cleanup_old_data(db)
            
        except Exception as e:
            logger.error(f"❌ Daily prices update failed: {e}", exc_info=True)
        finally:
            db.close()
    
    def update_financial_statements(self):
        """
        재무제표 업데이트 (전체 종목)
        - 분기별 실행 (2월, 4월, 7월, 10월)
        - 직전 분기 재무제표 수집
        """
        logger.info("📊 Starting scheduled financial statements update...")
        
        db: Session = SessionLocal()
        try:
            collector = DataCollector(db)
            stock_service = StockService(db)
            
            # 전체 활성 종목 조회
            stocks = stock_service.get_all_stocks(is_active=True, limit=10000)
            logger.info(f"   Found {len(stocks)} active stocks")
            
            # 현재 월에 따라 수집할 분기 결정
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # 분기 매핑: 2월(Q4), 4월(Q1), 7월(Q2), 10월(Q3)
            quarter_map = {
                2: (current_year - 1, 4),  # 전년도 Q4
                4: (current_year, 1),      # 올해 Q1
                7: (current_year, 2),      # 올해 Q2
                10: (current_year, 3)      # 올해 Q3
            }
            
            if current_month not in quarter_map:
                logger.warning(f"   Not a scheduled month for financial statements: {current_month}")
                return
            
            year, quarter = quarter_map[current_month]
            logger.info(f"   Collecting financial statements for {year}Q{quarter}")
            
            total_count = 0
            success_count = 0
            failed_count = 0
            
            # 각 종목별 수집
            for idx, stock in enumerate(stocks):
                try:
                    t, s, f = collector.collect_financial_statements(
                        stock.code,
                        year,
                        quarter
                    )
                    total_count += t
                    success_count += s
                    failed_count += f
                    
                    # 진행상황 로그 (100개마다)
                    if (idx + 1) % 100 == 0:
                        logger.info(f"   Progress: {idx + 1}/{len(stocks)} stocks processed")
                    
                    # API Rate Limit 방지 (DART API는 초당 제한이 있음)
                    import time
                    time.sleep(0.1)  # 100ms 대기
                    
                except Exception as e:
                    logger.error(f"   Failed to update {stock.code}: {e}")
                    failed_count += 1
            
            # 수집 로그 기록
            status = "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed")
            collector.create_collection_log(
                collection_type="financial_statement_scheduled",
                status=status,
                total_count=total_count,
                success_count=success_count,
                failed_count=failed_count,
                started_at=datetime.now(),
                completed_at=datetime.now()
            )
            
            logger.info(f"✅ Financial statements update completed: {success_count}/{total_count} succeeded")
            
        except Exception as e:
            logger.error(f"❌ Financial statements update failed: {e}", exc_info=True)
        finally:
            db.close()
    
    def run_now_daily_prices(self):
        """일봉 데이터 즉시 실행 (테스트용)"""
        logger.info("🔧 Running daily prices update immediately...")
        self.update_daily_prices()
    
    def run_now_financial_statements(self):
        """재무제표 즉시 실행 (테스트용)"""
        logger.info("🔧 Running financial statements update immediately...")
        self.update_financial_statements()
    
    def _cleanup_old_data(self, db: Session):
        """
        2년 이상 오래된 데이터 자동 삭제
        - 매일 일봉 업데이트 후 실행
        - 2년치 데이터만 유지 (롤링 윈도우)
        """
        try:
            from app.models.financial_data import DailyPrice
            
            cutoff_date = date.today() - timedelta(days=730)  # 2년 = 730일
            
            # 2년 이상 오래된 데이터 삭제
            deleted_count = db.query(DailyPrice).filter(
                DailyPrice.date < cutoff_date
            ).delete()
            
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"🗑️  Cleaned up {deleted_count} old daily price records (older than {cutoff_date})")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}", exc_info=True)
            db.rollback()


# 전역 스케줄러 인스턴스
_scheduler_instance = None


def get_scheduler() -> DataScheduler:
    """스케줄러 인스턴스 가져오기 (싱글톤)"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DataScheduler()
    return _scheduler_instance


def start_data_scheduler():
    """스케줄러 시작 (서버 시작 시 호출)"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_data_scheduler():
    """스케줄러 중지 (서버 종료 시 호출)"""
    scheduler = get_scheduler()
    scheduler.stop()
