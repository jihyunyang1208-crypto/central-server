"""
초기 데이터 수집 스크립트
- 전체 KRX 종목 리스트 수집
- 각 종목별 1년치 일봉 데이터 수집
- 최초 1회만 실행

실행 방법:
cd c:\\Users\\yangj\\AUT\\central-backend
python initial_data_collection.py
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import logging

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.services.data_collector import DataCollector
from app.services.stock_service import StockService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_initial_data():
    """초기 데이터 수집 (1회 실행)"""
    
    logger.info("=" * 80)
    logger.info("🚀 Starting initial data collection...")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        collector = DataCollector(db)
        stock_service = StockService(db)
        
        # ============================================
        # 1단계: 종목 리스트 수집
        # ============================================
        logger.info("\n📊 Step 1: Collecting stock list...")
        
        total, success, failed = collector.collect_stock_list(market=None)  # 전체 시장
        
        logger.info(f"   ✅ Stock list collected: {success}/{total} succeeded")
        
        if success == 0:
            logger.error("❌ Failed to collect stock list. Aborting.")
            return
        
        # ============================================
        # 2단계: 1년치 일봉 데이터 수집
        # ============================================
        logger.info("\n📈 Step 2: Collecting 2-year daily prices for all stocks...")
        
        # 날짜 범위 설정 (2년치)
        end_date = date.today()
        start_date = end_date - timedelta(days=730)  # 2년 = 730일
        
        logger.info(f"   Date range: {start_date} ~ {end_date}")
        
        # 전체 종목 조회
        stocks = stock_service.get_all_stocks(is_active=True, limit=10000)
        logger.info(f"   Found {len(stocks)} active stocks")
        
        total_count = 0
        success_count = 0
        failed_count = 0
        
        # 각 종목별 수집
        for idx, stock in enumerate(stocks):
            try:
                logger.info(f"\n   [{idx + 1}/{len(stocks)}] Collecting {stock.code} ({stock.name})...")
                
                t, s, f = collector.collect_daily_prices(
                    stock.code,
                    start_date,
                    end_date
                )
                
                total_count += t
                success_count += s
                failed_count += f
                
                logger.info(f"      ✓ Collected {s}/{t} records")
                
                # 진행상황 요약 (100개마다)
                if (idx + 1) % 100 == 0:
                    logger.info(f"\n   📊 Progress Summary:")
                    logger.info(f"      Stocks processed: {idx + 1}/{len(stocks)}")
                    logger.info(f"      Total records: {success_count}/{total_count}")
                    logger.info(f"      Success rate: {success_count/total_count*100:.1f}%")
                
            except Exception as e:
                logger.error(f"      ❌ Failed to collect {stock.code}: {e}")
                failed_count += 1
        
        # ============================================
        # 최종 결과
        # ============================================
        logger.info("\n" + "=" * 80)
        logger.info("✅ Initial data collection completed!")
        logger.info("=" * 80)
        logger.info(f"\n📊 Final Statistics:")
        logger.info(f"   Stocks processed: {len(stocks)}")
        logger.info(f"   Total records collected: {success_count:,}/{total_count:,}")
        logger.info(f"   Failed records: {failed_count:,}")
        logger.info(f"   Success rate: {success_count/total_count*100:.1f}%")
        logger.info(f"\n💾 Data saved to PostgreSQL database")
        logger.info(f"   Date range: {start_date} ~ {end_date}")
        
        # 수집 로그 기록
        collector.create_collection_log(
            collection_type="initial_bulk_load",
            status="success" if failed_count == 0 else "partial",
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            start_date=start_date,
            end_date=end_date,
            started_at=None,
            completed_at=None
        )
        
    except Exception as e:
        logger.error(f"\n❌ Initial data collection failed: {e}", exc_info=True)
    finally:
        db.close()
    
    logger.info("\n" + "=" * 80)
    logger.info("🎉 Initial setup complete! Daily scheduler will maintain data automatically.")
    logger.info("=" * 80)


if __name__ == "__main__":
    # 사용자 확인
    print("\n⚠️  This script will collect 2-year historical data for ALL KRX stocks.")
    print("   This may take 30-60 minutes depending on your internet connection.")
    print("   The script should only be run ONCE for initial setup.\n")
    
    response = input("Do you want to proceed? (yes/no): ")
    
    if response.lower() == 'yes':
        collect_initial_data()
    else:
        print("Initial data collection cancelled.")
