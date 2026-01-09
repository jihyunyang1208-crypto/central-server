from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from datetime import datetime
from app.core.database import Base
import enum

class InquiryStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SupportInquiry(Base):
    __tablename__ = "support_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), index=True)
    title = Column(String(255))
    content = Column(Text)
    status = Column(Enum(InquiryStatus), default=InquiryStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
