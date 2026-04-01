# central-backend/app/scheduler.py
"""
Scheduler for background tasks
- Auto-renewal payment processing
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import logging
from app.core.database import get_db
from app.services.auto_payment import check_and_process_renewals
from app.services.macro.service import execute_macro_analysis_cycle

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_renewal_check():
    """스케줄러에서 호출되는 동기 함수"""
    db = next(get_db())
    try:
        logger.info("🔄 Starting auto-renewal check...")
        asyncio.run(check_and_process_renewals(db))
        logger.info("✅ Auto-renewal check completed")
    except Exception as e:
        logger.error(f"❌ Renewal check failed: {e}", exc_info=True)
    finally:
        db.close()

def run_macro_analysis():
    """아침 스케줄러에서 08:30, 장마감 15:40 마다 수행할 거시경제 LLM 분석"""
    try:
        logger.info("🔄 Starting global macro analysis generation...")
        asyncio.run(execute_macro_analysis_cycle())
    except Exception as e:
        logger.error(f"❌ Macro analysis failed: {e}", exc_info=True)


def start_scheduler():
    """스케줄러 시작"""
    # 매일 오전 9시에 실행
    scheduler.add_job(
        run_renewal_check,
        CronTrigger(hour=9, minute=0),
        id='renewal_check',
        name='Check and process subscription renewals',
        replace_existing=True
    )
    
    scheduler.add_job(
        run_macro_analysis,
        CronTrigger(hour=8, minute=30),
        id='macro_analysis_morning',
        name='Generate Macro Analysis Morning (08:30)',
        replace_existing=True
    )

    scheduler.add_job(
        run_macro_analysis,
        CronTrigger(hour=15, minute=40),
        id='macro_analysis_afternoon',
        name='Generate Macro Analysis Afternoon (15:40)',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started - Auto-renewal check at 9:00 AM, Macro Analysis at 08:30/15:40")


def stop_scheduler():
    """스케줄러 중지"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Scheduler stopped")
