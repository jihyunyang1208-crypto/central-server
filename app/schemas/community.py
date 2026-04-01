# central-backend/app/schemas/community.py
"""
커뮤니티 기능 Pydantic 스키마 (요청/응답 직렬화)
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────
# Post Schemas
# ─────────────────────────────────────────────────────────

class PostCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=10)
    post_type: str = Field(default="free")
    condition_id: Optional[str] = None
    condition_name: Optional[str] = None

    # 유료 설정
    is_paid: bool = False
    credit_price: int = Field(default=0, ge=0)

    # AutoTrader 로컬 봇에서 생성된 인증 패키지 (선택)
    verification_payload: Optional[dict[str, Any]] = None


class PostUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    is_paid: Optional[bool] = None
    credit_price: Optional[int] = Field(None, ge=0)


class AuthorInfo(BaseModel):
    id: int
    email: str
    nickname: Optional[str] = None

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: int
    author_id: int
    title: str
    content: Optional[str] = None      # 유료 게시글이면 미열람 시 None
    post_type: str

    condition_id: Optional[str] = None
    condition_name: Optional[str] = None

    verification_status: str
    verified_at: Optional[datetime] = None

    # 요약 지표 (항상 공개)
    win_rate: Optional[float] = None
    total_pnl: Optional[float] = None
    roi_avg: Optional[float] = None
    trades_count: Optional[int] = None

    is_paid: bool
    credit_price: int
    has_access: bool = False            # 현재 사용자의 열람 권한

    view_count: int
    like_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────
# Comment Schemas
# ─────────────────────────────────────────────────────────

class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────
# Credit Schemas
# ─────────────────────────────────────────────────────────

class CreditBalanceResponse(BaseModel):
    user_id: int
    balance: int
    updated_at: Optional[datetime] = None


class CreditRechargeRequest(BaseModel):
    """크레딧 충전 요청 - 토스 결제 완료 후 호출"""
    payment_key: str
    order_id: str
    amount: int = Field(..., gt=0, description="결제 금액 (원)")


class CreditHistoryResponse(BaseModel):
    id: int
    event_type: str
    amount: int
    balance_after: int
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────
# Paid Access Schemas
# ─────────────────────────────────────────────────────────

class AccessPostRequest(BaseModel):
    post_id: int


class AccessPostResponse(BaseModel):
    success: bool
    credits_spent: int
    balance_after: int
    message: str
