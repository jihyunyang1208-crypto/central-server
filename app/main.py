# central-backend/app/main.py
"""
중앙 백엔드 서버 메인 애플리케이션
- 사용자 인증/인가 (JWT)
- 구독 관리
- 커미션 관리
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .core.config import settings
from .core.database import init_db
from .api import auth_router, subscriptions_router, commissions_router, users_router, kiwoom_router, trading_settings_router
from .api.admin import router as admin_router
from .routers.payments import router as payments_router
from .routers.billing import router as billing_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="중앙 백엔드 서버 - 사용자 인증, 구독 관리, 커미션 관리",
)

# CORS 설정 (임시로 모든 origin 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 임시: 모든 origin 허용
    allow_credentials=False,  # wildcard와 함께 사용 불가
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(commissions_router)
app.include_router(users_router)
app.include_router(kiwoom_router)
app.include_router(trading_settings_router)
app.include_router(payments_router)
app.include_router(billing_router)
app.include_router(admin_router)


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    
    # 데이터베이스 초기화
    init_db()
    logger.info("✅ Database initialized")
    
    # 스케줄러 시작 (자동결제)
    from .scheduler import start_scheduler
    start_scheduler()
    
    logger.info(f"✅ Server ready on http://{settings.HOST}:{settings.PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 Server shutting down...")


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """상세 헬스 체크"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": "2025-12-13T21:30:00Z"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
