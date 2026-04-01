from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.core.database import Base

class MacroAnalysisReport(Base):
    __tablename__ = "macro_analysis_reports"

    id = Column(Integer, primary_key=True, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    naver_source_text = Column(Text, nullable=True) # Raw text extracted from Naver AI
    youtube_source_text = Column(Text, nullable=True) # Raw transcript from Youtube
    report_content = Column(Text, nullable=False) # Final concatenated markdown
    
