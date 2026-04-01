# central-backend/run.py
"""
중앙 백엔드 서버 실행 스크립트
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # [NEW] Cloudflare Tunnel for External Access (Mobile)
    try:
        from app.utils.tunnel_manager import TunnelManager
        
        # Start tunnel for the backend port
        tm = TunnelManager(port=settings.PORT)
        public_url = tm.start()
        
        if public_url:
            print("\n" + "="*60)
            print(f"🚀 CENTRAL BACKEND IS LIVE AT: {public_url}")
            print("To use Mobile App, update your Vercel Environment Variable:")
            print(f"CENTRAL_API_URL={public_url}")
            print("="*60 + "\n")
            
    except Exception as e:
        print(f"⚠️ Failed to start tunnel: {e}")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
