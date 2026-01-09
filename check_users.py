"""
중앙 서버에서 사용자 ID 확인 스크립트
"""
import sys
import os

# central-backend 경로 추가
sys.path.insert(0, r"c:\Users\yangj\AUT\central-backend")
os.chdir(r"c:\Users\yangj\AUT\central-backend")

# .env 로드
from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    users = db.query(User).all()
    print("=== Central Server Users ===")
    print(f"Total users: {len(users)}\n")
    
    for u in users:
        print(f"ID: {u.id}")
        print(f"Email: {u.email}")
        print(f"Active: {u.is_active}")
        print(f"Admin: {getattr(u, 'is_admin', 'N/A')}")
        print(f"Created: {u.created_at}")
        print("-" * 40)
        
finally:
    db.close()
