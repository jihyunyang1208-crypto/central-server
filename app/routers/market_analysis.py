import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timezone

from app.core.database import SessionLocal
from app.models.macro_analysis import MacroAnalysisReport

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/market/macro-analysis",
    tags=["Market Analysis"]
)

@router.get("/latest")
async def get_latest_macro_analysis():
    """
    Fetch the most recently generated macroeconomic analysis report.
    """
    db = SessionLocal()
    try:
        report = db.query(MacroAnalysisReport).order_by(MacroAnalysisReport.generated_at.desc()).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="No macro analysis report available.")

        # [FIX] generated_at에 UTC 타임존 정보를 로 부여하여 JS가 KST로 올바르게 변환하도록함
        generated_at = report.generated_at
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
            
        return {
            "status": "success",
            "data": {
                "id": report.id,
                "generated_at": generated_at.isoformat(),
                "content": report.report_content
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch latest macro analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        db.close()


@router.post("/trigger")
async def trigger_macro_analysis(background_tasks: BackgroundTasks):
    """
    [Admin] 수동으로 거시 경제 분석 스케줄러를 즉시 실행합니다.
    """
    from app.services.macro.service import execute_macro_analysis_cycle
    background_tasks.add_task(execute_macro_analysis_cycle)
    return {"status": "accepted", "message": "타임라인 분석이 백그라운드에서 시작되었습니다. 1여 분 후 치시가 갱신됩니다."}
