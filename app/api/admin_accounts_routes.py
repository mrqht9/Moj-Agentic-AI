#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Admin Routes لإدارة الحسابات
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user, require_admin
from app.services.account_service import account_service

router = APIRouter(prefix="/api/admin/accounts", tags=["Admin - Accounts"])


class AccountResponse(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_name: Optional[str]
    platform: str
    username: str
    display_name: Optional[str]
    account_label: Optional[str]
    category: Optional[str]
    nationality: Optional[str]
    status: str
    last_login: Optional[str]
    last_used: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str


class AccountStatsResponse(BaseModel):
    total: int
    active: int
    inactive: int
    expired: int
    error: int
    by_platform: dict


@router.get("/", response_model=List[AccountResponse])
async def get_all_accounts(
    platform: Optional[str] = Query(None, description="تصفية حسب المنصة"),
    status: Optional[str] = Query(None, description="تصفية حسب الحالة"),
    limit: int = Query(100, ge=1, le=500, description="الحد الأقصى للنتائج"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    الحصول على جميع الحسابات (للإدارة فقط)
    
    - **platform**: x, instagram, facebook, linkedin, tiktok
    - **status**: active, inactive, expired, error
    """
    accounts = account_service.get_all_accounts_admin(
        db=db,
        platform=platform,
        status=status,
        limit=limit
    )
    
    return accounts


@router.get("/stats", response_model=AccountStatsResponse)
async def get_accounts_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """الحصول على إحصائيات الحسابات (للإدارة فقط)"""
    stats = account_service.get_account_stats(db=db)
    return stats


@router.delete("/{account_id}")
async def delete_account_admin(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    حذف حساب (للإدارة فقط)
    
    يحذف الحساب من قاعدة البيانات وملف الكوكيز
    """
    account = account_service.get_account_by_id(db, account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")
    
    # الإدارة يمكنها حذف أي حساب
    success = account_service.delete_account(db, account_id, account.user_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="فشل حذف الحساب")
    
    return {
        "success": True,
        "message": f"تم حذف الحساب {account.username} على {account.platform}",
        "account_id": account_id
    }


@router.patch("/{account_id}/status")
async def update_account_status_admin(
    account_id: int,
    status: str = Query(..., regex="^(active|inactive|expired|error)$"),
    error_message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    تحديث حالة الحساب (للإدارة فقط)
    
    - **status**: active, inactive, expired, error
    """
    account = account_service.update_account_status(
        db=db,
        account_id=account_id,
        status=status,
        error_message=error_message
    )
    
    if not account:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")
    
    return {
        "success": True,
        "message": f"تم تحديث حالة الحساب إلى {status}",
        "account": {
            "id": account.id,
            "username": account.username,
            "platform": account.platform,
            "status": account.status
        }
    }


@router.get("/user/{user_id}", response_model=List[AccountResponse])
async def get_user_accounts_admin(
    user_id: int,
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """الحصول على حسابات مستخدم معين (للإدارة فقط)"""
    accounts = account_service.get_user_accounts(
        db=db,
        user_id=user_id,
        platform=platform
    )
    
    result = []
    for account in accounts:
        user = db.query(User).filter(User.id == account.user_id).first()
        result.append({
            "id": account.id,
            "user_id": account.user_id,
            "user_email": user.email if user else None,
            "user_name": user.name if user else None,
            "platform": account.platform,
            "username": account.username,
            "display_name": account.display_name,
            "account_label": account.account_label,
            "category": account.category,
            "nationality": account.nationality,
            "status": account.status,
            "last_login": account.last_login.isoformat() if account.last_login else None,
            "last_used": account.last_used.isoformat() if account.last_used else None,
            "error_message": account.error_message,
            "created_at": account.created_at.isoformat(),
            "updated_at": account.updated_at.isoformat()
        })
    
    return result
