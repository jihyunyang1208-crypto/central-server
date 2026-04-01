"""
Manually trigger a fresh Macro Analysis cycle.
Run this once after fixing the Gemini API key issue to overwrite the stale error report.

Usage:
    cd c:/Users/yangj/AUT/central-backend
    py trigger_macro_analysis.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from app.services.macro_analysis_service import (
    execute_macro_analysis_cycle,
    get_gemini_api_key_from_db,
)


async def main():
    logger.info("=" * 60)
    logger.info("Manual Macro Analysis Trigger")
    logger.info("=" * 60)

    # 1) Gemini API 키 확인
    api_key = get_gemini_api_key_from_db()
    if not api_key:
        logger.error("❌ Gemini API key not found in DB or .env!")
        logger.error("   Run: py save_gemini_config.py  (with your key)")
        sys.exit(1)

    masked = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else api_key[:4] + "..."
    logger.info(f"✅ API Key loaded: {masked}")
    logger.info("🚀 Starting data pipeline (Naver scraping + YouTube + Gemini)...")
    logger.info("   This may take 1-3 minutes. Please wait...")

    # 2) 파이프라인 실행
    await execute_macro_analysis_cycle()

    logger.info("=" * 60)
    logger.info("✅ Done! Refresh the dashboard to see the new report.")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
