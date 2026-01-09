from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models.support import InquiryStatus

class SupportInquiryCreate(BaseModel):
    user_email: EmailStr
    title: Optional[str] = "일반 문의"
    content: str

class SupportInquiryResponse(BaseModel):
    id: int
    user_email: str
    title: str
    content: str
    status: InquiryStatus
    created_at: datetime

    class Config:
        from_attributes = True
