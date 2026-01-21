from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import User, XAccount, Conversation, Message, SocialAccount
from app.auth.admin_dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class SocialAccountInfo(BaseModel):
    id: int
    platform: str
    username: str
    status: str
    last_login: Optional[str] = None
    last_used: Optional[str] = None


class ConversationInfo(BaseModel):
    id: int
    title: Optional[str] = None
    messages_count: int
    created_at: str
    updated_at: str


class UserListResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: str
    x_accounts_count: int
    conversations_count: int
    social_accounts_count: int
    
    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: str
    social_accounts: List[SocialAccountInfo]
    conversations: List[ConversationInfo]
    total_messages: int
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    admin_users: int
    total_x_accounts: int
    users_created_today: int


class UpdateUserRequest(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
    success: bool


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = db.query(User).filter(User.is_active == False).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    total_x_accounts = db.query(XAccount).count()
    
    today = datetime.utcnow().date()
    users_created_today = db.query(User).filter(
        func.date(User.created_at) == today
    ).count()
    
    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        admin_users=admin_users,
        total_x_accounts=total_x_accounts,
        users_created_today=users_created_today
    )


@router.get("/users", response_model=List[UserListResponse])
async def get_all_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    users = db.query(User).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        # عدد المحادثات
        conversations_count = db.query(Conversation).filter(
            Conversation.user_id == user.id
        ).count()
        
        # عدد الحسابات الاجتماعية
        social_accounts_count = db.query(SocialAccount).filter(
            SocialAccount.user_id == user.id
        ).count()
        
        result.append(UserListResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            profile_picture=user.profile_picture,
            is_admin=user.is_admin,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            x_accounts_count=len(user.x_accounts),
            conversations_count=conversations_count,
            social_accounts_count=social_accounts_count
        ))
    
    return result


@router.put("/users/{user_id}", response_model=UserListResponse)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == admin_user.id and request.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.name is not None:
        user.name = request.name
    
    db.commit()
    db.refresh(user)
    
    return UserListResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        profile_picture=user.profile_picture,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        x_accounts_count=len(user.x_accounts)
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """الحصول على تفاصيل المستخدم الكاملة مع المحادثات والحسابات"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # الحسابات الاجتماعية
    social_accounts = db.query(SocialAccount).filter(
        SocialAccount.user_id == user_id
    ).all()
    
    social_accounts_info = [
        SocialAccountInfo(
            id=acc.id,
            platform=acc.platform,
            username=acc.username,
            status=acc.status,
            last_login=acc.last_login.isoformat() if acc.last_login else None,
            last_used=acc.last_used.isoformat() if acc.last_used else None
        )
        for acc in social_accounts
    ]
    
    # المحادثات
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).all()
    
    conversations_info = []
    total_messages = 0
    
    for conv in conversations:
        messages_count = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()
        total_messages += messages_count
        
        conversations_info.append(ConversationInfo(
            id=conv.id,
            title=conv.title,
            messages_count=messages_count,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat()
        ))
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        profile_picture=user.profile_picture,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        social_accounts=social_accounts_info,
        conversations=conversations_info,
        total_messages=total_messages
    )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return MessageResponse(
        message=f"User {user.email} deleted successfully",
        success=True
    )
