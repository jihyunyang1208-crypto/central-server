
# central-backend/app/utils/tunnel_manager.py
import subprocess
import re
import threading
import time
import requests
import logging
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TunnelManager")

class TunnelManager:
    """Cloudflare Tunnel 관리자"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self.stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """터널 시작 및 URL 모니터링"""
        if self._thread and self._thread.is_alive():
            return
            
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._run_tunnel, daemon=True)
        self._thread.start()
        
        # URL 획득 대기 (최대 30초)
        start_time = time.time()
        while time.time() - start_time < 30:
            if self.public_url:
                logger.info(f"Cloudflare Tunnel started at: {self.public_url}")
                return self.public_url
            time.sleep(1)
            
        logger.warning("Failed to obtain Cloudflare Tunnel URL within timeout.")
        return None

    def stop(self):
        """터널 종료"""
        self.stop_event.set()
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            logger.info("Cloudflare Tunnel stopped.")

    def _run_tunnel(self):
        """터널 프로세스 실행 및 출력 파싱 (LocalTunnel 사용)"""
        try:
            # LocalTunnel 실행 (고정 서브도메인 사용)
            # Windows에서는 npx.cmd를 호출해야 함
            import os
            executable = "npx.cmd" if os.name == 'nt' else "npx"
            subdomain = "aut-central-temporary"
            
            cmd = [executable, "localtunnel", "--port", str(self.port), "--subdomain", subdomain]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # LocalTunnel은 URL을 stdout에 출력함
            # "your url is: https://..."
            
            while not self.stop_event.is_set():
                if self.process.poll() is not None:
                    break
                
                # stdout에서 읽기
                line = self.process.stdout.readline()
                if not line:
                    continue
                    
                line = line.strip()
                if "your url is:" in line:
                    self.public_url = line.split("your url is: ")[1].strip()
                    logger.info(f"🌍 Fixed Public URL detected: {self.public_url}")
                    # URL 획득 성공
                    
        except FileNotFoundError:
            logger.error("npx executable not found. Please install Node.js.")
        except Exception as e:
            logger.error(f"Error running localtunnel: {e}")
        finally:
            if self.process:
                self.process.terminate()
