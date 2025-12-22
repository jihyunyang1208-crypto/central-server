"""
Admin middleware for role-based access control
Protects admin-only routes
"""

from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin privileges
    Raises 403 Forbidden if user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
