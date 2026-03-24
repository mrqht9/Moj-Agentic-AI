#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أدوات الوكلاء الذكية
Tools for AI Agents
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.utils.secure_logger import get_secure_logger

logger = get_secure_logger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.intent_service import intent_service
from app.services import x_bridge
from app.x.modules.utils import safe_label

# مسار حفظ الكوكيز
BASE_DIR = Path(__file__).resolve().parent.parent
COOKIES_DIR = BASE_DIR / "x" / "cookies"
COOKIES_DIR.mkdir(exist_ok=True, parents=True)

# Thread pool للعمليات المتزامنة
executor = ThreadPoolExecutor(max_workers=3)


def detect_user_intent(text: str) -> Dict[str, Any]:
    """
    أداة تحليل نوايا المستخدم
    
    Args:
        text: النص المدخل من المستخدم
        
    Returns:
        نتيجة تحليل النية مع الكيانات والمنصة المستهدفة
    """
    result = intent_service.detect_intent(text)
    return result.to_dict()


def _x_login_sync(username: str, password: str, label: str, headless: bool = True, user_id: Optional[int] = None) -> Dict[str, Any]:
    """تسجيل الدخول عبر API سيرفر app/x"""
    try:
        safe_username = safe_label(username)
        print(f"[Tools] تسجيل دخول عبر API: label={safe_username}, username={username}")

        result = x_bridge.login(
            label=safe_username,
            username=username,
            password=password,
            headless=headless,
        )

        if not result.get("success"):
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {"success": False, "message": f"فشل تسجيل الدخول: {error}"}

        cookie_filename = result.get("filename", f"{safe_username}.json")

        # حفظ في قاعدة البيانات إذا كان user_id متوفراً
        if user_id:
            try:
                from app.db.database import SessionLocal
                from app.services.account_service import account_service
                from datetime import datetime

                db = SessionLocal()
                try:
                    existing = account_service.get_account_by_username(
                        db=db, user_id=user_id, platform="x", username=username
                    )
                    if existing:
                        account_service.update_account(
                            db=db, account_id=existing.id,
                            status="active", last_login=datetime.utcnow(),
                            cookie_filename=cookie_filename, error_message=None
                        )
                    else:
                        account_service.create_account(
                            db=db, user_id=user_id, platform="x",
                            username=username, display_name=username,
                            account_label=username, cookie_filename=cookie_filename
                        )
                finally:
                    db.close()
            except Exception as e:
                print(f"[ERROR] Failed to save account to database: {e}")

        return {
            "success": True,
            "message": f"تم تسجيل الدخول بنجاح وحفظ الحساب باسم '{username}'",
            "label": username,
            "filename": cookie_filename
        }
    except Exception as e:
        return {"success": False, "message": f"فشل تسجيل الدخول: {str(e)}"}


def x_delete_account(account_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    حذف حساب X من النظام
    
    Args:
        account_name: اسم الحساب (username)
        user_id: معرف المستخدم (اختياري)
    
    Returns:
        نتيجة عملية الحذف
    """
    try:
        safe_account = safe_label(account_name)
        cookie_file = COOKIES_DIR / f"{safe_account}.json"
        
        deleted_items = []
        
        # 1. حذف ملف الكوكيز
        if cookie_file.exists():
            try:
                cookie_file.unlink()
                deleted_items.append(f"✅ تم حذف ملف الكوكيز: {cookie_file.name}")
                print(f"[DEBUG] Deleted cookie file: {cookie_file}")
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ فشل حذف ملف الكوكيز: {str(e)}"
                }
        else:
            deleted_items.append(f"⚠️ ملف الكوكيز غير موجود")
        
        # 2. حذف من قاعدة البيانات إذا كان user_id متوفراً
        if user_id:
            try:
                from app.db.database import SessionLocal
                from app.services.account_service import account_service
                
                print(f"[DEBUG] Attempting to delete account from database: user_id={user_id}, username={account_name}")
                
                db = SessionLocal()
                try:
                    # البحث عن الحساب
                    existing = account_service.get_account_by_username(
                        db=db,
                        user_id=user_id,
                        platform="x",
                        username=account_name
                    )
                    
                    if existing:
                        # حذف الحساب
                        print(f"[DEBUG] Deleting account: id={existing.id}, username={existing.username}, status={existing.status}")
                        result = account_service.delete_account(db=db, account_id=existing.id, user_id=user_id)
                        
                        if result:
                            deleted_items.append(f"✅ تم حذف الحساب من قاعدة البيانات")
                            print(f"[DEBUG] Account deleted successfully from database: {existing.id}")
                        else:
                            deleted_items.append(f"⚠️ فشل حذف الحساب من قاعدة البيانات")
                            print(f"[ERROR] Failed to delete account from database: {existing.id}")
                    else:
                        deleted_items.append(f"⚠️ الحساب غير موجود في قاعدة البيانات")
                finally:
                    db.close()
            except Exception as e:
                import traceback
                print(f"[ERROR] Failed to delete account from database: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                deleted_items.append(f"⚠️ تحذير: لم يتم الحذف من قاعدة البيانات: {str(e)}")
        
        # تجميع النتيجة
        if len(deleted_items) > 0:
            message = f"🗑️ **تم حذف الحساب '{account_name}'**\n\n"
            message += "\n".join(deleted_items)
            return {
                "success": True,
                "message": message
            }
        else:
            return {
                "success": False,
                "message": f"❌ الحساب '{account_name}' غير موجود في النظام"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ فشل حذف الحساب: {str(e)}"
        }


def x_login(username: str, password: str, label: str, headless: bool = True, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    تسجيل الدخول إلى منصة X (Twitter)
    
    Args:
        username: اسم المستخدم
        password: كلمة المرور
        label: اسم الحساب للحفظ
        headless: تشغيل المتصفح في الخلفية
        user_id: معرف المستخدم (لحفظ في قاعدة البيانات)
        
    Returns:
        نتيجة عملية تسجيل الدخول
    """
    try:
        # تشغيل في thread منفصل لتجنب تعارض asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        
        if loop and loop.is_running():
            # نحن داخل asyncio loop، استخدم thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_login_sync, username, password, label, headless, user_id)
                return future.result(timeout=300)  # 5 دقائق timeout
        else:
            # لا يوجد asyncio loop، نفذ مباشرة
            return _x_login_sync(username, password, label, headless, user_id)
    
    except Exception as e:
        return {
            "success": False,
            "message": f"خطأ في تسجيل الدخول: {str(e)}"
        }


def _x_post_sync(label: str, text: str, media_url: Optional[str] = None, headless: bool = True) -> Dict[str, Any]:
    """نشر تغريدة عبر API سيرفر app/x"""
    try:
        label = safe_label(label)
        print(f"[Tools] نشر تغريدة عبر API: label={label}, text='{text[:50]}...'")

        result = x_bridge.post_tweet(
            cookie_label=label,
            text=text,
            media_url=media_url or "",
            headless=headless,
        )

        print(f"[Tools] نتيجة API: {result}")

        if result.get("success"):
            msg = result.get("message", "تم النشر")
            tweet_url = result.get("tweet_url")
            print(f"[Tools] tweet_url extracted: {tweet_url}")
            full_msg = f"✅ {msg} على حساب '{label}'"
            if tweet_url:
                full_msg += f"\n🔗 {tweet_url}"
            return {"success": True, "message": full_msg}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {
                "success": False,
                "message": f"❌ فشل النشر من حساب '{label}'\n\n📋 **تفاصيل:** {error}"
            }

    except Exception as e:
        return {"success": False, "message": f"فشل النشر: {str(e)}"}


def x_post(label: str, text: str, media_url: Optional[str] = None, headless: bool = True) -> Dict[str, Any]:
    """
    نشر تغريدة على منصة X
    
    Args:
        label: اسم الحساب المحفوظ
        text: نص التغريدة
        media_url: رابط الصورة أو الفيديو (اختياري)
        headless: تشغيل المتصفح في الخلفية
        
    Returns:
        نتيجة عملية النشر
    """
    try:
        # تشغيل في thread منفصل لتجنب تعارض asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        
        if loop and loop.is_running():
            # نحن داخل asyncio loop، استخدم thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_post_sync, label, text, media_url, headless)
                return future.result(timeout=300)
        else:
            # لا يوجد asyncio loop، نفذ مباشرة
            return _x_post_sync(label, text, media_url, headless)
    
    except Exception as e:
        return {
            "success": False,
            "message": f"خطأ في النشر: {str(e)}"
        }


def x_delete_tweet(label: str, tweet_id: str, headless: bool = True) -> Dict[str, Any]:
    """
    حذف تغريدة من منصة X
    
    Args:
        label: اسم الحساب المحفوظ
        tweet_id: معرف التغريدة
        headless: تشغيل المتصفح في الخلفية
        
    Returns:
        نتيجة عملية الحذف
    """
    try:
        label = safe_label(label)
        print(f"[Tools] حذف تغريدة عبر API: label={label}, tweet_id={tweet_id}")

        result = x_bridge.delete_tweet(
            cookie_label=label,
            tweet_id=tweet_id,
            headless=headless,
        )

        print(f"[Tools] نتيجة حذف API: {result}")

        if result.get("success"):
            msg = result.get("message", "تم الحذف")
            return {"success": True, "message": f"✅ {msg} من حساب '{label}'"}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {
                "success": False,
                "message": f"❌ فشل حذف التغريدة من حساب '{label}'\n\n📋 **تفاصيل:** {error}"
            }

    except Exception as e:
        return {"success": False, "message": f"فشل الحذف: {str(e)}"}


def _x_update_profile_sync(
    label: str,
    name: Optional[str] = None,
    bio: Optional[str] = None,
    location: Optional[str] = None,
    website: Optional[str] = None,
    avatar_url: Optional[str] = None,
    banner_url: Optional[str] = None,
    headless: bool = True
) -> Dict[str, Any]:
    """تحديث الملف الشخصي عبر API سيرفر app/x"""
    try:
        label = safe_label(label)
        print(f"[Tools] تحديث ملف شخصي عبر API: label={label}")

        result = x_bridge.update_profile(
            cookie_label=label,
            name=name or "",
            bio=bio or "",
            location=location or "",
            website=website or "",
            avatar_url=avatar_url or "",
            banner_url=banner_url or "",
            headless=headless,
        )

        if result.get("success"):
            msg = result.get("message", "تم التحديث")
            return {"success": True, "message": f"✅ {msg} لحساب '{label}'"}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {"success": False, "message": f"فشل التحديث: {error}"}
    except Exception as e:
        return {"success": False, "message": f"فشل التحديث: {str(e)}"}


def x_update_profile(
    label: str,
    name: Optional[str] = None,
    bio: Optional[str] = None,
    location: Optional[str] = None,
    website: Optional[str] = None,
    avatar_url: Optional[str] = None,
    banner_url: Optional[str] = None,
    headless: bool = True
) -> Dict[str, Any]:
    """
    تحديث معلومات الملف الشخصي على منصة X
    
    Args:
        label: اسم الحساب المحفوظ
        name: الاسم الجديد
        bio: السيرة الذاتية
        location: الموقع
        website: الموقع الإلكتروني
        avatar_url: رابط الصورة الشخصية
        banner_url: رابط صورة الغلاف
        headless: تشغيل المتصفح في الخلفية
        
    Returns:
        نتيجة عملية التحديث
    """
    try:
        # تشغيل في thread منفصل لتجنب تعارض asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        
        if loop and loop.is_running():
            # نحن داخل asyncio loop، استخدم thread pool
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_update_profile_sync, label, name, bio, location, website, avatar_url, banner_url, headless)
                return future.result(timeout=300)
        else:
            # لا يوجد asyncio loop، نفذ مباشرة
            return _x_update_profile_sync(label, name, bio, location, website, avatar_url, banner_url, headless)
    
    except Exception as e:
        return {
            "success": False,
            "message": f"خطأ في التحديث: {str(e)}"
        }
