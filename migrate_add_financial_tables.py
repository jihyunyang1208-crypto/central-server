"""
데이터베이스 마이그레이션 스크립트
재무 데이터 테이블 생성

실행 방법:
cd c:\\Users\\yangj\\AUT\\central-backend
python migrate_add_financial_tables.py
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import engine, Base
from app.models.financial_data import StockInfo, DailyPrice, FinancialStatement, Disclosure, DataCollectionLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """재무 데이터 테이블 생성"""
    logger.info("🔧 Starting financial data tables migration...")
    
    try:
        # 테이블 존재 여부 확인
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('stock_info', 'daily_prices', 'financial_statements', 'disclosures', 'data_collection_logs')
            """))
            existing_tables = [row[0] for row in result]
        
        if existing_tables:
            logger.warning(f"⚠️  Following tables already exist: {existing_tables}")
            response = input("Do you want to drop and recreate them? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Migration cancelled.")
                return
            
            # 기존 테이블 삭제
            logger.info("🗑️  Dropping existing tables...")
            with engine.connect() as conn:
                for table in ['data_collection_logs', 'disclosures', 'financial_statements', 'daily_prices', 'stock_info']:
                    if table in existing_tables:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                        conn.commit()
                        logger.info(f"   ✓ Dropped {table}")
        
        # 새 테이블 생성
        logger.info("📊 Creating financial data tables...")
        Base.metadata.create_all(bind=engine, tables=[
            StockInfo.__table__,
            DailyPrice.__table__,
            FinancialStatement.__table__,
            Disclosure.__table__,
            DataCollectionLog.__table__,
        ])
        
        logger.info("✅ Migration completed successfully!")
        logger.info("\n📋 Created tables:")
        logger.info("   ✓ stock_info - 종목 기본 정보")
        logger.info("   ✓ daily_prices - 일봉 가격 데이터 (이평선 포함)")
        logger.info("   ✓ financial_statements - 재무제표 데이터")
        logger.info("   ✓ disclosures - 공시 정보")
        logger.info("   ✓ data_collection_logs - 데이터 수집 로그")
        
        # 테이블 확인
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' 
                AND table_name IN ('stock_info', 'daily_prices', 'financial_statements', 'disclosures', 'data_collection_logs')
                ORDER BY table_name
            """))
            
            logger.info("\n📊 Table summary:")
            for row in result:
                logger.info(f"   {row[0]}: {row[1]} columns")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    migrate()
