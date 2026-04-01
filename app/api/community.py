# central-backend/app/api/community.py
"""
커뮤니티 API 라우터
- 게시글 CRUD
- 크레딧 잔액 조회 및 충전
- 유료 게시글 열람 (크레딧 소모)
- 댓글 CRUD
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.community import (
    CommunityPost, Comment, UserCredit, CreditHistory, PaidAccess,
    VerificationStatus, CreditEventType
)
from ..models.user import User
from ..schemas.community import (
    PostCreateRequest, PostUpdateRequest, PostResponse, PostListResponse,
    CommentCreateRequest, CommentResponse,
    CreditBalanceResponse, CreditRechargeRequest, CreditHistoryResponse,
    AccessPostRequest, AccessPostResponse,
)
from ..core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/community", tags=["Community"])

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

CREDIT_PER_KRW = 100  # 1 크레딧 = 100원


def _get_or_create_credit(db: Session, user_id: int) -> UserCredit:
    credit = db.query(UserCredit).filter(UserCredit.user_id == user_id).first()
    if not credit:
        credit = UserCredit(user_id=user_id, balance=0)
        db.add(credit)
        db.flush()
    return credit


def _has_access(db: Session, user_id: int, post: CommunityPost) -> bool:
    """현재 사용자가 유료 게시글에 접근 가능한지 확인"""
    if not post.is_paid:
        return True
    if post.author_id == user_id:
        return True
    access = db.query(PaidAccess).filter(
        PaidAccess.user_id == user_id,
        PaidAccess.post_id == post.id
    ).first()
    return access is not None


def _build_post_response(db: Session, post: CommunityPost, current_user_id: int) -> PostResponse:
    """게시글을 PostResponse로 변환. 유료 + 미열람자는 content를 None 처리"""
    has_acc = _has_access(db, current_user_id, post)
    return PostResponse(
        id=post.id,
        author_id=post.author_id,
        title=post.title,
        content=post.content if has_acc else None,
        post_type=post.post_type,
        condition_id=post.condition_id,
        condition_name=post.condition_name,
        verification_status=post.verification_status,
        verified_at=post.verified_at,
        win_rate=post.win_rate,
        total_pnl=post.total_pnl,
        roi_avg=post.roi_avg,
        trades_count=post.trades_count,
        is_paid=post.is_paid,
        credit_price=post.credit_price,
        has_access=has_acc,
        view_count=post.view_count,
        like_count=post.like_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


# ─────────────────────────────────────────────────────────
# Post Endpoints
# ─────────────────────────────────────────────────────────

@router.get("/posts", response_model=PostListResponse)
def list_posts(
    post_type: Optional[str]  = Query(None, description="조건식/전략/분석/자유"),
    verified_only: bool        = Query(False, description="인증된 게시글만"),
    page: int                  = Query(1, ge=1),
    page_size: int             = Query(20, ge=1, le=100),
    db: Session                = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    """게시글 목록 조회"""
    q = db.query(CommunityPost).filter(
        CommunityPost.is_deleted == False,
        CommunityPost.is_hidden  == False,
    )
    if post_type:
        q = q.filter(CommunityPost.post_type == post_type)
    if verified_only:
        q = q.filter(CommunityPost.verification_status == VerificationStatus.VERIFIED.value)

    total = q.count()
    posts = q.order_by(CommunityPost.created_at.desc()) \
             .offset((page - 1) * page_size).limit(page_size).all()

    return PostListResponse(
        posts=[_build_post_response(db, p, current_user.id) for p in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    db: Session    = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """게시글 상세 조회 (조회수 증가)"""
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id,
        CommunityPost.is_deleted == False
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    post.view_count = (post.view_count or 0) + 1
    db.commit()
    return _build_post_response(db, post, current_user.id)


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    req: PostCreateRequest,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """게시글 작성 (인증 패키지 포함 가능)"""
    new_post = CommunityPost(
        author_id      = current_user.id,
        title          = req.title,
        content        = req.content,
        post_type      = req.post_type,
        condition_id   = req.condition_id,
        condition_name = req.condition_name,
        is_paid        = req.is_paid,
        credit_price   = req.credit_price if req.is_paid else 0,
    )

    # 인증 패키지가 있으면 파싱 후 저장
    if req.verification_payload:
        new_post = _apply_verification_payload(new_post, req.verification_payload)

    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    logger.info(f"✅ Community post created: id={new_post.id} by user={current_user.id}")
    return _build_post_response(db, new_post, current_user.id)


def _apply_verification_payload(post: CommunityPost, payload: dict) -> CommunityPost:
    """인증 패키지의 요약 지표를 게시글 모델에 적용"""
    from datetime import datetime, timezone, timedelta
    summary = payload.get("summary", {})
    post.verification_payload  = payload
    post.verification_status   = VerificationStatus.VERIFIED.value
    post.verified_at           = datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
    post.win_rate              = summary.get("win_rate")
    post.total_pnl             = summary.get("total_pnl")
    post.roi_avg               = summary.get("roi_avg")
    post.trades_count          = summary.get("trades_count")
    return post


@router.patch("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    req: PostUpdateRequest,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """게시글 수정 (작성자만)"""
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id,
        CommunityPost.is_deleted == False
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

    if req.title   is not None: post.title        = req.title
    if req.content is not None: post.content      = req.content
    if req.is_paid is not None: post.is_paid      = req.is_paid
    if req.credit_price is not None:
        post.credit_price = req.credit_price if post.is_paid else 0

    db.commit()
    db.refresh(post)
    return _build_post_response(db, post, current_user.id)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """게시글 삭제 (소프트 삭제, 작성자만)"""
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id,
        CommunityPost.is_deleted == False
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

    post.is_deleted = True
    db.commit()


# ─────────────────────────────────────────────────────────
# Credit Endpoints
# ─────────────────────────────────────────────────────────

@router.get("/credits/balance", response_model=CreditBalanceResponse)
def get_credit_balance(
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """현재 크레딧 잔액 조회"""
    credit = _get_or_create_credit(db, current_user.id)
    db.commit()
    return CreditBalanceResponse(user_id=current_user.id, balance=credit.balance, updated_at=credit.updated_at)


@router.post("/credits/recharge")
def recharge_credits(
    req: CreditRechargeRequest,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """크레딧 충전 (토스 결제 완료 후 호출)
    - 1크레딧 = 100원 환산
    - 실제 결제 검증은 payments.py (토스 webhook)에서 처리
    """
    credits_to_add = req.amount // CREDIT_PER_KRW
    if credits_to_add <= 0:
        raise HTTPException(status_code=400, detail=f"최소 {CREDIT_PER_KRW}원 이상 충전해야 합니다.")

    credit = _get_or_create_credit(db, current_user.id)
    credit.balance += credits_to_add

    history = CreditHistory(
        user_id       = current_user.id,
        event_type    = CreditEventType.RECHARGE.value,
        amount        = credits_to_add,
        balance_after = credit.balance,
        payment_key   = req.payment_key,
        description   = f"크레딧 충전 ({req.amount:,}원 → {credits_to_add}크레딧)",
    )
    db.add(history)
    db.commit()

    logger.info(f"💳 Credit recharged: user={current_user.id}, +{credits_to_add} credits (total={credit.balance})")
    return {"success": True, "credits_added": credits_to_add, "balance": credit.balance}


@router.get("/credits/history", response_model=list[CreditHistoryResponse])
def get_credit_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """크레딧 거래 내역 조회"""
    histories = db.query(CreditHistory).filter(
        CreditHistory.user_id == current_user.id
    ).order_by(CreditHistory.created_at.desc()).limit(limit).all()
    return histories


# ─────────────────────────────────────────────────────────
# Paid Access Endpoint
# ─────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/access", response_model=AccessPostResponse)
def access_paid_post(
    post_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """유료 게시글 크레딧으로 열람 잠금 해제"""
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id,
        CommunityPost.is_deleted == False
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if not post.is_paid:
        raise HTTPException(status_code=400, detail="무료 게시글입니다.")
    if _has_access(db, current_user.id, post):
        return AccessPostResponse(success=True, credits_spent=0, balance_after=0, message="이미 열람 권한이 있습니다.")

    credit = _get_or_create_credit(db, current_user.id)
    if credit.balance < post.credit_price:
        raise HTTPException(
            status_code=402,
            detail=f"크레딧이 부족합니다. (필요: {post.credit_price}, 보유: {credit.balance})"
        )

    credit.balance -= post.credit_price

    history = CreditHistory(
        user_id       = current_user.id,
        event_type    = CreditEventType.SPEND.value,
        amount        = -post.credit_price,
        balance_after = credit.balance,
        post_id       = post.id,
        description   = f"게시글 열람: '{post.title[:30]}'",
    )
    db.add(history)

    access = PaidAccess(
        user_id       = current_user.id,
        post_id       = post.id,
        credits_spent = post.credit_price,
    )
    db.add(access)
    db.commit()

    logger.info(f"🔓 Paid access granted: user={current_user.id}, post={post_id}, cost={post.credit_price}")
    return AccessPostResponse(
        success=True,
        credits_spent=post.credit_price,
        balance_after=credit.balance,
        message="열람 권한이 부여되었습니다.",
    )


# ─────────────────────────────────────────────────────────
# Comment Endpoints
# ─────────────────────────────────────────────────────────

@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
def list_comments(
    post_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comments = db.query(Comment).filter(
        Comment.post_id    == post_id,
        Comment.is_deleted == False,
    ).order_by(Comment.created_at.asc()).all()
    return comments


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    post_id: int,
    req: CommentCreateRequest,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(
        CommunityPost.id == post_id, CommunityPost.is_deleted == False
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    comment = Comment(post_id=post_id, author_id=current_user.id, content=req.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session        = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(
        Comment.id      == comment_id,
        Comment.post_id == post_id,
        Comment.is_deleted == False,
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

    comment.is_deleted = True
    db.commit()
