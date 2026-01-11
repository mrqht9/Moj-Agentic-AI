from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db.models import User
from app.db.redis_client import RedisClient
from app.auth.security import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Middleware to get current authenticated user from JWT token"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    # Check if token is blacklisted
    if RedisClient.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication - returns None if no valid token"""
    
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    # Check if token is blacklisted
    if RedisClient.is_blacklisted(token):
        return None
    
    # Decode token
    token_data = decode_token(token)
    if token_data is None:
        return None
    
    # Get user from database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    return user


def require_permission(permission: str):
    """Decorator factory for permission checking (extensible)"""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        # Add permission logic here if needed
        # For now, just check if user exists
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return permission_checker
