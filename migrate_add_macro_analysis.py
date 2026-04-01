import sqlite3
import os
import sys

# 프로젝트 루트 참조
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "central.db")

def migrate():
    print(f"[Migration] Using database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. MacroAnalysisReport 테이블 생성
        print("[Migration] Creating macro_analysis_reports table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_analysis_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            naver_source_text TEXT,
            youtube_source_text TEXT,
            report_content TEXT NOT NULL
        )
        """)
        
        # 2. 인덱스 생성
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS ix_macro_analysis_reports_generated_at
        ON macro_analysis_reports (generated_at)
        """)
        
        conn.commit()
        print("[Migration] SQLite migration successfully completed!")
        
    except Exception as e:
        conn.rollback()
        print(f"[Migration] Error occurred during migration: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
