#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User Routes لإدارة الحسابات الشخصية
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.services.account_service import account_service

router = APIRouter(prefix="/api/my/accounts", tags=["User - My Accounts"])


class MyAccountResponse(BaseModel):
    id: int
    platform: str
    username: str
    display_name: Optional[str]
    account_label: Optional[str]
    status: str
    last_login: Optional[str]
    last_used: Optional[str]
    created_at: str


@router.get("/", response_model=List[MyAccountResponse])
async def get_my_accounts(
    platform: Optional[str] = Query(None, description="تصفية حسب المنصة"),
    status: Optional[str] = Query(None, description="تصفية حسب الحالة"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    الحصول على حساباتي
    
    - **platform**: x, instagram, facebook, linkedin, tiktok
    - **status**: active, inactive, expired, error
    """
    accounts = account_service.get_user_accounts(
        db=db,
        user_id=current_user.id,
        platform=platform,
        status=status
    )
    
    return [
        {
            "id": account.id,
            "platform": account.platform,
            "username": account.username,
            "display_name": account.display_name,
            "account_label": account.account_label,
            "status": account.status,
            "last_login": account.last_login.isoformat() if account.last_login else None,
            "last_used": account.last_used.isoformat() if account.last_used else None,
            "created_at": account.created_at.isoformat()
        }
        for account in accounts
    ]


@router.get("/stats")
async def get_my_accounts_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على إحصائيات حساباتي"""
    stats = account_service.get_account_stats(db=db, user_id=current_user.id)
    return stats


@router.delete("/{account_id}")
async def delete_my_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    حذف أحد حساباتي
    
    يحذف الحساب من قاعدة البيانات وملف الكوكيز
    """
    account = account_service.get_account_by_id(db, account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")
    
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية لحذف هذا الحساب")
    
    success = account_service.delete_account(db, account_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=500, detail="فشل حذف الحساب")
    
    return {
        "success": True,
        "message": f"تم حذف الحساب {account.username} على {account.platform}",
        "account_id": account_id
    }


@router.get("/{account_id}")
async def get_my_account_details(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """الحصول على تفاصيل حساب معين"""
    account = account_service.get_account_by_id(db, account_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="الحساب غير موجود")
    
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية لعرض هذا الحساب")
    
    return {
        "id": account.id,
        "platform": account.platform,
        "username": account.username,
        "display_name": account.display_name,
        "account_label": account.account_label,
        "status": account.status,
        "last_login": account.last_login.isoformat() if account.last_login else None,
        "last_used": account.last_used.isoformat() if account.last_used else None,
        "error_message": account.error_message,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat()
    }
