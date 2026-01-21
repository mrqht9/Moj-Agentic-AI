#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
X Platform API Routes
API endpoints لإدارة منصة X (Twitter)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pathlib import Path
import tempfile
import os

from app.x.modules.x_login import TwitterLoginAdvanced
from app.x.modules.x_post import post_to_x
from app.x.modules.x_profile import update_profile_on_x
from app.x.modules.utils import download_to_temp, is_url, safe_label
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/x", tags=["X Platform"])

# مسار حفظ الكوكيز
BASE_DIR = Path(__file__).resolve().parent.parent
COOKIES_DIR = BASE_DIR / "x" / "cookies"
COOKIES_DIR.mkdir(exist_ok=True, parents=True)


class XLoginRequest(BaseModel):
    """طلب تسجيل دخول X"""
    label: str = Field(..., description="اسم الحساب")
    username: str = Field(..., description="اسم المستخدم")
    password: str = Field(..., description="كلمة المرور")
    headless: bool = Field(default=True, description="تشغيل المتصفح في الخلفية")


class XLoginResponse(BaseModel):
    """استجابة تسجيل دخول X"""
    success: bool
    message: str
    label: str
    filename: Optional[str] = None
    timestamp: str


class XPostRequest(BaseModel):
    """طلب نشر على X"""
    label: str = Field(..., description="اسم الحساب")
    text: str = Field(..., description="نص التغريدة")
    media_url: Optional[str] = Field(None, description="رابط الصورة/الفيديو")
    headless: bool = Field(default=True, description="تشغيل المتصفح في الخلفية")


class XPostResponse(BaseModel):
    """استجابة النشر على X"""
    success: bool
    message: str
    timestamp: str


class XProfileUpdateRequest(BaseModel):
    """طلب تحديث الملف الشخصي"""
    label: str = Field(..., description="اسم الحساب")
    name: Optional[str] = Field(None, description="الاسم")
    bio: Optional[str] = Field(None, description="السيرة الذاتية")
    location: Optional[str] = Field(None, description="الموقع")
    website: Optional[str] = Field(None, description="الموقع الإلكتروني")
    avatar_url: Optional[str] = Field(None, description="رابط الصورة الشخصية")
    banner_url: Optional[str] = Field(None, description="رابط صورة الغلاف")
    headless: bool = Field(default=True, description="تشغيل المتصفح في الخلفية")


@router.post("/login", response_model=XLoginResponse)
async def x_login(
    request: XLoginRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    تسجيل الدخول إلى حساب X وحفظ الكوكيز
    
    Args:
        request: بيانات تسجيل الدخول
        current_user: المستخدم الحالي
    
    Returns:
        نتيجة تسجيل الدخول
    """
    try:
        label = safe_label(request.label)
        
        # تسجيل الدخول
        engine = TwitterLoginAdvanced()
        cookie_path = engine.login_twitter(
            username=request.username,
            password=request.password,
            cookies_dir=str(COOKIES_DIR),
            headless=request.headless
        )
        
        # إعادة تسمية الملف
        dst = COOKIES_DIR / f"{label}.json"
        try:
            if Path(cookie_path).name != dst.name:
                Path(cookie_path).replace(dst)
        except Exception:
            pass
        
        return XLoginResponse(
            success=True,
            message="تم تسجيل الدخول وحفظ الكوكيز بنجاح",
            label=label,
            filename=dst.name,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"فشل تسجيل الدخول: {str(e)}"
        )


@router.post("/post", response_model=XPostResponse)
async def x_post(
    request: XPostRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    نشر تغريدة على X
    
    Args:
        request: بيانات التغريدة
        current_user: المستخدم الحالي
    
    Returns:
        نتيجة النشر
    """
    try:
        label = safe_label(request.label)
        cookie_file = COOKIES_DIR / f"{label}.json"
        
        if not cookie_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"الحساب '{label}' غير موجود. يجب تسجيل الدخول أولاً."
            )
        
        storage_state_path = str(cookie_file)
        
        # تحميل الميديا إذا كان هناك رابط
        with tempfile.TemporaryDirectory() as tmp:
            media_path = None
            if request.media_url and is_url(request.media_url):
                try:
                    media_path = download_to_temp(request.media_url, tmp)
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"فشل تنزيل الميديا: {str(e)}"
                    )
            
            # النشر
            post_to_x(
                storage_state_path=storage_state_path,
                text=request.text,
                media_path=media_path,
                headless=request.headless
            )
        
        return XPostResponse(
            success=True,
            message="تم نشر التغريدة بنجاح",
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"فشل النشر: {str(e)}"
        )


@router.post("/profile/update")
async def x_profile_update(
    request: XProfileUpdateRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    تحديث الملف الشخصي على X
    
    Args:
        request: بيانات التحديث
        current_user: المستخدم الحالي
    
    Returns:
        نتيجة التحديث
    """
    try:
        label = safe_label(request.label)
        cookie_file = COOKIES_DIR / f"{label}.json"
        
        if not cookie_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"الحساب '{label}' غير موجود. يجب تسجيل الدخول أولاً."
            )
        
        storage_state_path = str(cookie_file)
        
        # تحميل الصور إذا كانت روابط
        with tempfile.TemporaryDirectory() as tmp:
            avatar_path = None
            banner_path = None
            
            if request.avatar_url and is_url(request.avatar_url):
                try:
                    avatar_path = download_to_temp(request.avatar_url, tmp)
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"فشل تنزيل الصورة الشخصية: {str(e)}"
                    )
            
            if request.banner_url and is_url(request.banner_url):
                try:
                    banner_path = download_to_temp(request.banner_url, tmp)
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"فشل تنزيل صورة الغلاف: {str(e)}"
                    )
            
            # تحديث الملف الشخصي
            update_profile_on_x(
                storage_state_path=storage_state_path,
                name=request.name,
                bio=request.bio,
                location=request.location,
                website=request.website,
                avatar_path=avatar_path,
                banner_path=banner_path,
                headless=request.headless
            )
        
        return {
            "success": True,
            "message": "تم تحديث الملف الشخصي بنجاح",
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"فشل تحديث الملف الشخصي: {str(e)}"
        )


@router.get("/accounts")
async def list_x_accounts(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    عرض قائمة حسابات X المحفوظة
    
    Returns:
        قائمة الحسابات
    """
    try:
        accounts = []
        
        if COOKIES_DIR.exists():
            for cookie_file in COOKIES_DIR.glob("*.json"):
                accounts.append({
                    "label": cookie_file.stem,
                    "filename": cookie_file.name,
                    "created_at": datetime.fromtimestamp(cookie_file.stat().st_ctime).isoformat()
                })
        
        return {
            "success": True,
            "accounts": accounts,
            "count": len(accounts),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في عرض الحسابات: {str(e)}"
        )


@router.delete("/accounts/{label}")
async def delete_x_account(
    label: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    حذف حساب X
    
    Args:
        label: اسم الحساب
        current_user: المستخدم الحالي
    
    Returns:
        نتيجة الحذف
    """
    try:
        label = safe_label(label)
        cookie_file = COOKIES_DIR / f"{label}.json"
        
        if not cookie_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"الحساب '{label}' غير موجود"
            )
        
        cookie_file.unlink()
        
        return {
            "success": True,
            "message": f"تم حذف الحساب '{label}' بنجاح",
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في حذف الحساب: {str(e)}"
        )


@router.get("/health")
async def x_health_check():
    """فحص صحة نظام X"""
    return {
        "status": "healthy",
        "service": "X Platform",
        "cookies_dir": str(COOKIES_DIR),
        "accounts_count": len(list(COOKIES_DIR.glob("*.json"))) if COOKIES_DIR.exists() else 0,
        "timestamp": datetime.now().isoformat()
    }
