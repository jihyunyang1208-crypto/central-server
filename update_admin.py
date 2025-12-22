"""
Admin 계정 업데이트 스크립트
jihyun.yang.1208@gmail.com을 admin으로 설정하고 비밀번호 변경
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def update_admin_account():
    db = SessionLocal()
    
    try:
        email = "jihyun.yang.1208@gmail.com"
        new_password = "didwlgus87!@#"
        
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"[ERROR] User {email} not found")
            return
        
        # Update password and admin status
        user.hashed_password = get_password_hash(new_password)
        user.is_admin = True
        
        db.commit()
        
        print("="*60)
        print("ADMIN ACCOUNT UPDATED")
        print("="*60)
        print(f"Email: {email}")
        print(f"Password: {new_password}")
        print(f"Admin: True")
        print(f"User ID: {user.id}")
        print("="*60)
        print("\n[SUCCESS] Admin account updated successfully!")
        
    except Exception as e:
        print(f"[ERROR] Failed to update admin account: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_account()
