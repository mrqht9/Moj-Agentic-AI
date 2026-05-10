#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
X Platform API Routes
API endpoints لإدارة منصة X (Twitter)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import tempfile
import os
import json
import time

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


class XUploadCookiesResponse(BaseModel):
    """استجابة رفع كوكيز X"""
    success: bool
    message: str
    label: str
    filename: Optional[str] = None
    timestamp: str


def _convert_to_playwright_format(cookies_data) -> dict:
    """
    تحويل الكوكيز إلى صيغة Playwright إذا لم تكن بالصيغة الصحيحة.
    
    يدعم:
    - صيغة extension/browser: [{"name": ..., "value": ..., "domain": ..., "expirationDate": ...}, ...]
    - صيغة Playwright: {"cookies": [...], "origins": []}
    - صيغة dict بسيطة: {"auth_token": "...", "ct0": "..."}
    """
    HTTP_ONLY = {'auth_token', 'kdt', '_twitter_sess', '__cf_bm', 'auth_multi'}
    LAX_COOKIES = {'ct0', 'auth_multi'}
    
    # إذا كانت بصيغة Playwright بالفعل
    if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
        cookie_list = cookies_data['cookies']
        # تحقق أن الكوكيز تحتوي على الحقول المطلوبة
        if cookie_list and all(k in cookie_list[0] for k in ('name', 'value', 'domain')):
            # تأكد من وجود حقل expires (بدل expirationDate)
            needs_conversion = any('expirationDate' in c and 'expires' not in c for c in cookie_list)
            if not needs_conversion:
                return cookies_data
    
    # إذا كانت مصفوفة (صيغة extension)
    if isinstance(cookies_data, list):
        cookie_list = cookies_data
    elif isinstance(cookies_data, dict) and 'cookies' in cookies_data:
        cookie_list = cookies_data['cookies']
    elif isinstance(cookies_data, dict):
        # صيغة dict بسيطة {key: value}
        cookie_list = []
        for k, v in cookies_data.items():
            cookie_list.append({
                "name": k,
                "value": str(v),
                "domain": ".x.com",
                "path": "/",
                "expirationDate": time.time() + 365 * 24 * 3600,
                "httpOnly": k in HTTP_ONLY,
                "secure": True,
            })
    else:
        raise ValueError("صيغة كوكيز غير معروفة")
    
    # تحويل إلى صيغة Playwright
    playwright_cookies = []
    for c in cookie_list:
        name = c.get('name', '')
        expires = c.get('expires') or c.get('expirationDate') or (time.time() + 365 * 24 * 3600)
        
        same_site_raw = c.get('sameSite', 'None')
        if same_site_raw in ('no_restriction', None):
            same_site = 'None'
        elif same_site_raw == 'lax':
            same_site = 'Lax'
        elif same_site_raw == 'strict':
            same_site = 'Strict'
        else:
            same_site = same_site_raw if same_site_raw in ('None', 'Lax', 'Strict') else 'None'
        
        if name in LAX_COOKIES:
            same_site = 'Lax'
        
        playwright_cookies.append({
            "name": name,
            "value": c.get('value', ''),
            "domain": c.get('domain', '.x.com'),
            "path": c.get('path', '/'),
            "expires": float(expires),
            "httpOnly": c.get('httpOnly', name in HTTP_ONLY),
            "secure": c.get('secure', True),
            "sameSite": same_site,
        })
    
    return {"cookies": playwright_cookies, "origins": []}


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


@router.post("/login")
async def x_login_disabled(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    تسجيل الدخول بالباسورد معطّل.
    يجب رفع ملف كوكيز بدلاً من ذلك عبر /api/x/upload-cookies
    """
    raise HTTPException(
        status_code=403,
        detail="تسجيل الدخول بكلمة المرور معطّل. يرجى رفع ملف كوكيز الحساب عبر /api/x/upload-cookies"
    )


@router.post("/upload-cookies", response_model=XUploadCookiesResponse)
async def x_upload_cookies(
    cookie_file: UploadFile = File(..., description="ملف كوكيز الحساب (JSON)"),
    label: Optional[str] = Form(None, description="اسم الحساب (اختياري — إذا لم يُحدد يُستخدم اسم الملف)"),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    رفع ملف كوكيز لحساب X وحفظه بصيغة Playwright.
    
    - إذا كان الملف بصيغة extension (مصفوفة) يتم تحويله تلقائياً لصيغة Playwright.
    - اسم الحساب يُأخذ من label أو من اسم الملف المرفوع.
    """
    try:
        # قراءة الملف
        content = await cookie_file.read()
        try:
            cookies_data = json.loads(content.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"ملف الكوكيز غير صالح (ليس JSON): {str(e)}")
        
        # تحديد اسم الحساب
        if label:
            account_name = safe_label(label.strip())
        else:
            # استخدم اسم الملف بدون امتداد
            raw_name = cookie_file.filename or "account"
            account_name = safe_label(Path(raw_name).stem)
        
        if not account_name:
            raise HTTPException(status_code=400, detail="اسم الحساب فارغ")
        
        # تحويل إلى صيغة Playwright
        playwright_data = _convert_to_playwright_format(cookies_data)
        
        # التحقق من وجود auth_token
        cookie_names = {c['name'] for c in playwright_data.get('cookies', [])}
        if 'auth_token' not in cookie_names:
            raise HTTPException(status_code=400, detail="ملف الكوكيز لا يحتوي على auth_token — تأكد أن الكوكيز صالحة")
        
        # حفظ الملف
        dst = COOKIES_DIR / f"{account_name}.json"
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(playwright_data, f, ensure_ascii=False, indent=2)
        
        return XUploadCookiesResponse(
            success=True,
            message=f"تم حفظ كوكيز الحساب '{account_name}' بنجاح",
            label=account_name,
            filename=dst.name,
            timestamp=datetime.now().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"فشل حفظ الكوكيز: {str(e)}"
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
