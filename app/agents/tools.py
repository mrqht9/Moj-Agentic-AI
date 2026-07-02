#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أدوات الوكلاء الذكية
Tools for AI Agents
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.utils.secure_logger import get_secure_logger

logger = get_secure_logger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.intent_service import intent_service
from app.services import x_bridge
from app.x.modules.utils import safe_label
from app.api.x_routes import _convert_to_playwright_format

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


def _x_save_cookies_sync(cookies_data: Union[str, dict, list], label: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """حفظ كوكيز حساب X مباشرة (بدون تسجيل دخول)"""
    try:
        account_name = safe_label(label)
        if not account_name:
            return {"success": False, "message": "اسم الحساب فارغ"}
        
        print(f"[Tools] حفظ كوكيز حساب: {account_name}")
        
        # تحويل من JSON string إذا لزم الأمر
        if isinstance(cookies_data, str):
            cookies_data = json.loads(cookies_data)
        
        # تحويل إلى صيغة Playwright
        playwright_data = _convert_to_playwright_format(cookies_data)
        
        # التحقق من وجود auth_token
        cookie_names = {c['name'] for c in playwright_data.get('cookies', [])}
        if 'auth_token' not in cookie_names:
            return {"success": False, "message": "ملف الكوكيز لا يحتوي على auth_token — تأكد أن الكوكيز صالحة"}
        
        # حفظ الملف
        dst = COOKIES_DIR / f"{account_name}.json"
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(playwright_data, f, ensure_ascii=False, indent=2)
        
        cookie_filename = dst.name
        
        # تسجيل في قاعدة بيانات X Suite
        try:
            from app.x.modules.db import upsert_cookie
            upsert_cookie(account_name, cookie_filename)
            print(f"[Tools] ✅ تم تسجيل '{account_name}' في X Suite DB")
        except Exception as e:
            print(f"[Tools] ⚠️ فشل تسجيل في X Suite DB: {e}")
        
        # حفظ في قاعدة البيانات إذا كان user_id متوفراً
        if user_id:
            try:
                from app.db.database import SessionLocal
                from app.services.account_service import account_service
                from datetime import datetime

                db = SessionLocal()
                try:
                    existing = account_service.get_account_by_username(
                        db=db, user_id=user_id, platform="x", username=account_name
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
                            username=account_name, display_name=account_name,
                            account_label=account_name, cookie_filename=cookie_filename
                        )
                finally:
                    db.close()
            except Exception as e:
                print(f"[ERROR] Failed to save account to database: {e}")
        
        return {
            "success": True,
            "message": f"تم حفظ كوكيز الحساب '{account_name}' بنجاح",
            "label": account_name,
            "filename": cookie_filename
        }
    except json.JSONDecodeError:
        return {"success": False, "message": "الكوكيز المقدمة ليست بصيغة JSON صالحة"}
    except Exception as e:
        return {"success": False, "message": f"فشل حفظ الكوكيز: {str(e)}"}


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


def x_upload_cookies(cookies_data: Union[str, dict, list], label: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    حفظ كوكيز حساب X (بدلاً من تسجيل الدخول بالباسورد)
    
    Args:
        cookies_data: بيانات الكوكيز (JSON string أو dict أو list)
        label: اسم الحساب للحفظ
        user_id: معرف المستخدم (لحفظ في قاعدة البيانات)
        
    Returns:
        نتيجة عملية الحفظ
    """
    try:
        return _x_save_cookies_sync(cookies_data, label, user_id)
    except Exception as e:
        return {
            "success": False,
            "message": f"خطأ في حفظ الكوكيز: {str(e)}"
        }


def x_login(username: str, password: str, label: str, headless: bool = True, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    تسجيل الدخول بالباسورد معطّل.
    يرجى رفع كوكيز الحساب بدلاً من ذلك.
    """
    return {
        "success": False,
        "message": "⛔ تسجيل الدخول بكلمة المرور معطّل.\n\nيرجى إرفاق ملف كوكيز الحساب بدلاً من ذلك.\n📎 ارفق ملف JSON يحتوي على كوكيز الحساب وسيتم حفظه تلقائياً."
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
            return {"success": True, "message": full_msg, "tweet_url": tweet_url}
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


# ── إعجاب ──
def _x_like_sync(label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    try:
        label = safe_label(label)
        result = x_bridge.like(cookie_label=label, tweet_url=tweet_url, headless=headless)
        if result.get("success"):
            return {"success": True, "message": f"✅ تم الإعجاب بالتغريدة من حساب '{label}'"}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {"success": False, "message": f"❌ فشل الإعجاب: {error}"}
    except Exception as e:
        return {"success": False, "message": f"فشل الإعجاب: {str(e)}"}


def x_like(label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    """إعجاب بتغريدة على منصة X"""
    try:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_like_sync, label, tweet_url, headless)
                return future.result(timeout=120)
        else:
            return _x_like_sync(label, tweet_url, headless)
    except Exception as e:
        return {"success": False, "message": f"خطأ في الإعجاب: {str(e)}"}


# ── إعادة نشر (ريتويت) ──
def _x_repost_sync(label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    try:
        label = safe_label(label)
        result = x_bridge.repost(cookie_label=label, tweet_url=tweet_url, headless=headless)
        if result.get("success"):
            return {"success": True, "message": f"✅ تمت إعادة النشر من حساب '{label}'"}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {"success": False, "message": f"❌ فشل إعادة النشر: {error}"}
    except Exception as e:
        return {"success": False, "message": f"فشل إعادة النشر: {str(e)}"}


def x_repost(label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    """إعادة نشر تغريدة على منصة X"""
    try:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_repost_sync, label, tweet_url, headless)
                return future.result(timeout=120)
        else:
            return _x_repost_sync(label, tweet_url, headless)
    except Exception as e:
        return {"success": False, "message": f"خطأ في إعادة النشر: {str(e)}"}


# ── متابعة ──
def _x_follow_sync(label: str, profile_url: str, headless: bool = True) -> Dict[str, Any]:
    try:
        label = safe_label(label)
        result = x_bridge.follow(cookie_label=label, profile_url=profile_url, headless=headless)
        if result.get("success"):
            return {"success": True, "message": f"✅ تمت متابعة الحساب من '{label}'"}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {"success": False, "message": f"❌ فشل المتابعة: {error}"}
    except Exception as e:
        return {"success": False, "message": f"فشل المتابعة: {str(e)}"}


def x_follow(label: str, profile_url: str, headless: bool = True) -> Dict[str, Any]:
    """متابعة حساب على منصة X"""
    try:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_follow_sync, label, profile_url, headless)
                return future.result(timeout=120)
        else:
            return _x_follow_sync(label, profile_url, headless)
    except Exception as e:
        return {"success": False, "message": f"خطأ في المتابعة: {str(e)}"}


# ── إلغاء متابعة ──
def x_unfollow(label: str, profile_url: str, headless: bool = True) -> Dict[str, Any]:
    """إلغاء متابعة حساب على منصة X"""
    try:
        label = safe_label(label)
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(x_bridge.unfollow, cookie_label=label, profile_url=profile_url, headless=headless)
                result = future.result(timeout=120)
        else:
            result = x_bridge.unfollow(cookie_label=label, profile_url=profile_url, headless=headless)
        if result.get("success"):
            return {"success": True, "message": f"✅ تم إلغاء المتابعة من حساب '{label}'"}
        else:
            error = result.get("message") or result.get("error") or "خطأ غير معروف"
            return {"success": False, "message": f"❌ فشل إلغاء المتابعة: {error}"}
    except Exception as e:
        return {"success": False, "message": f"خطأ في إلغاء المتابعة: {str(e)}"}


# ── رد على تغريدة ──
def _x_reply_sync(label: str, tweet_url: str, reply_text: str, headless: bool = True) -> Dict[str, Any]:
    try:
        label = safe_label(label)
        result = x_bridge.reply(cookie_label=label, tweet_url=tweet_url, reply_text=reply_text, headless=headless)
        if result.get("success"):
            return {"success": True, "message": f"✅ تم الرد على التغريدة من حساب '{label}'"}
        else:
            error = result.get("message") or result.get("error", "خطأ غير معروف")
            return {"success": False, "message": f"❌ فشل الرد: {error}"}
    except Exception as e:
        return {"success": False, "message": f"فشل الرد: {str(e)}"}


def x_reply(label: str, tweet_url: str, reply_text: str, headless: bool = True) -> Dict[str, Any]:
    """الرد على تغريدة على منصة X"""
    try:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_x_reply_sync, label, tweet_url, reply_text, headless)
                return future.result(timeout=120)
        else:
            return _x_reply_sync(label, tweet_url, reply_text, headless)
    except Exception as e:
        return {"success": False, "message": f"خطأ في الرد: {str(e)}"}


# ── حفظ تغريدة (بوكمارك) ──
def x_bookmark(label: str, tweet_url: str, headless: bool = True) -> Dict[str, Any]:
    """حفظ تغريدة في المفضلة على منصة X"""
    try:
        label = safe_label(label)
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(x_bridge.bookmark, cookie_label=label, tweet_url=tweet_url, headless=headless)
                result = future.result(timeout=120)
        else:
            result = x_bridge.bookmark(cookie_label=label, tweet_url=tweet_url, headless=headless)
        if result.get("success"):
            return {"success": True, "message": f"✅ تم حفظ التغريدة في المفضلة من حساب '{label}'"}
        else:
            return {"success": False, "message": f"❌ فشل الحفظ: {result.get('error', 'خطأ')}"}
    except Exception as e:
        return {"success": False, "message": f"خطأ في الحفظ: {str(e)}"}


# ── تسجيل دخول حساب X عبر LDPlayer (loginx) ──
LOGINX_BASE_URL = "http://127.0.0.1:5000"
LOGINX_API_KEY = "sk-loginx-2026-secret"


def x_login_account(username: str, password: str, email: str = "", headless: bool = False, user_id: Optional[int] = None) -> Dict[str, Any]:
    """تسجيل دخول حساب X عبر LDPlayer + Chrome automation (غير متزامن — لا يعلّق المحادثة).

    Args:
        user_id: معرّف مستخدم موج — لو موجود راح يُسجَّل الحساب في DB تلقائياً
                 بعد نجاح الدخول، ويظهر في "حساباتي".
    """
    import requests

    try:
        username = username.strip()
        password = password.strip()

        if not username or not password:
            return {"success": False, "message": "⚠️ اسم المستخدم وكلمة المرور مطلوبين"}

        # إرسال طلب التسجيل + callback_url لاستلام إشعار اكتمال في الشات
        headers = {"X-API-Key": LOGINX_API_KEY, "Content-Type": "application/json"}
        # موج يشتغل افتراضياً على 8000 — يقبل callback من localhost فقط
        callback_url = "http://127.0.0.1:8000/api/internal/login-callback"
        payload = {
            "username": username, "password": password, "email": email,
            "headless": headless, "user_id": user_id,
            "callback_url": callback_url,
        }

        resp = requests.post(f"{LOGINX_BASE_URL}/api/login", json=payload, headers=headers, timeout=10)
        data = resp.json()
        
        if not data.get("success"):
            return {"success": False, "message": f"❌ فشل بدء التسجيل: {data.get('error', 'خطأ')}"}
        
        session_id = data.get("session_id")
        mode = "مخفي 👻" if headless else "ظاهر 🖥️"
        
        return {
            "success": True,
            "message": (
                f"🚀 **بدأت عملية تسجيل الدخول لحساب '{username}'**\n\n"
                f"📋 **المعرّف:** `{session_id}`\n"
                f"🖥️ **وضع المحاكي:** {mode}\n\n"
                f"⏳ العملية تعمل بالخلفية — يمكنك متابعة استخدام موج بشكل عادي.\n\n"
                f"💡 للاستعلام عن الحالة اكتب: `حالة التسجيل`"
            ),
            "session_id": session_id
        }
        
    except requests.ConnectionError:
        return {
            "success": False,
            "message": "❌ سيرفر LoginX غير متصل!\n\nتأكد من تشغيل سيرفر loginx على بورت 5000:\n`cd app/x/loginx && python app.py`"
        }
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ في تسجيل الدخول: {str(e)}"}


def x_login_status(session_id: str = "") -> Dict[str, Any]:
    """استعلام عن حالة عملية تسجيل الدخول"""
    import requests
    
    try:
        headers = {"X-API-Key": LOGINX_API_KEY}
        
        # إذا ما عطى session_id، نجيب آخر عملية
        if not session_id:
            # نجرب نجيب آخر task
            resp = requests.get(f"{LOGINX_BASE_URL}/api/cookies", headers=headers, timeout=5)
            return {"success": True, "message": "💡 استخدم: `حالة التسجيل SESSION_ID`\n\nأو اكتب `حالة التسجيل` بعد بدء عملية تسجيل دخول."}
        
        resp = requests.get(f"{LOGINX_BASE_URL}/api/status/{session_id}", headers=headers, timeout=10)
        data = resp.json()
        
        status = data.get("status", "unknown")
        results = data.get("results", [])
        
        if status == "running":
            return {"success": True, "message": f"⏳ **العملية قيد التنفيذ...**\n\nالمعرّف: `{session_id}`"}
        elif status == "done":
            success_count = sum(1 for r in results if r.get("success"))
            total = len(results)
            lines = [f"✅ **اكتملت العملية:** {success_count}/{total} حساب نجح\n"]
            for r in results:
                icon = "✅" if r.get("success") else "❌"
                lines.append(f"{icon} {r.get('username')}")
            return {"success": True, "message": "\n".join(lines)}
        else:
            return {"success": True, "message": f"ℹ️ الحالة: {status}"}
            
    except requests.ConnectionError:
        return {"success": False, "message": "❌ سيرفر LoginX غير متصل"}
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ: {str(e)}"}


# ────────────────────────────────────────────────────────────────────
# سحب/عرض التايم لاين الشخصي لحسابات X المسجّلة
# ────────────────────────────────────────────────────────────────────

def x_fetch_timeline(account_name: str, count: int = 50, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    يسحب Home Timeline للحساب باستخدام كوكيزه (auth_token + ct0) ويحفظ
    التغريدات في قاعدة بيانات موج (data/x_timeline.db).

    Args:
        account_name: اسم الحساب المسجّل في موج (يوزرنيم)
        count: عدد التغريدات المطلوب سحبها (افتراضي 50)
        user_id: معرف مستخدم موج (اختياري - لربط التغريدات بمستخدم)
    """
    try:
        from app.services.x_timeline_service import fetch_and_save_timeline
        safe_account = safe_label(account_name)
        if not safe_account:
            return {"success": False, "message": "⚠️ اسم الحساب فارغ"}

        try:
            count = int(count)
        except (ValueError, TypeError):
            count = 50
        # حد أعلى لمنع الإفراط
        count = max(1, min(count, 500))

        result = fetch_and_save_timeline(
            account_username=safe_account,
            count=count,
            user_id=user_id,
        )

        if not result.get("success"):
            return {"success": False, "message": result.get("message", "❌ فشل سحب التايم لاين")}

        return {
            "success": True,
            "message": (
                f"🎉 **تم سحب التايم لاين لحساب '{safe_account}'**\n\n"
                f"📥 عدد التغريدات المسحوبة: **{result['total_fetched']}**\n"
                f"💾 عدد المحفوظة في قاعدة البيانات: **{result['saved']}**\n\n"
                f"💡 لعرضها اكتب: `اعرض تغريدات {safe_account}` "
                f"أو `اعرض التايم لاين حساب {safe_account}`"
            ),
        }
    except Exception as e:
        import traceback
        print(f"[x_fetch_timeline] error: {traceback.format_exc()}")
        return {"success": False, "message": f"❌ خطأ أثناء سحب التايم لاين: {str(e)}"}


# ────────────────────────────────────────────────────────────────────
# تصنيفات الحسابات
# ────────────────────────────────────────────────────────────────────

# التصنيفات المدعومة + تسمياتها العربية للعرض
CATEGORY_LABELS = {
    "social": ("اجتماعي", "👥"),
    "political": ("سياسي", "🏛️"),
    "sports": ("رياضي", "⚽"),
    "tech": ("تقني", "💻"),
    "religious": ("ديني", "🕌"),
    "entertainment": ("ترفيهي", "🎬"),
    "news": ("إخباري", "📰"),
    "literary": ("أدبي", "📚"),
    "business": ("تجاري", "💼"),
    "general": ("عام", "🌐"),
}


def _cat_label(code: Optional[str]) -> str:
    """يرجع التسمية العربية + إيموجي للتصنيف."""
    if not code:
        return "غير مصنف"
    if code in CATEGORY_LABELS:
        ar, emoji = CATEGORY_LABELS[code]
        return f"{emoji} {ar}"
    return code


def x_set_account_category(account_name: str, category: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    يحدّد/يغيّر تصنيف حساب معيّن.

    Args:
        account_name: اسم الحساب
        category: التصنيف (social/political/sports/tech/...)
        user_id: معرّف المستخدم
    """
    try:
        if not user_id:
            return {"success": False, "message": "⚠️ لتحديد التصنيف يجب تسجيل الدخول"}

        safe_account = safe_label(account_name)
        if not safe_account:
            return {"success": False, "message": "⚠️ اسم الحساب فارغ"}

        cat = (category or "").strip().lower()
        if cat not in CATEGORY_LABELS:
            valid = ", ".join(CATEGORY_LABELS.keys())
            return {
                "success": False,
                "message": (
                    f"⚠️ التصنيف '{category}' غير معروف.\n\n"
                    f"**التصنيفات المتاحة:**\n"
                    + "\n".join(f"• {code} — {ar} {emoji}"
                                for code, (ar, emoji) in CATEGORY_LABELS.items())
                ),
            }

        from app.db.database import SessionLocal
        from app.services.account_service import account_service

        db = SessionLocal()
        try:
            account = account_service.set_account_category(
                db=db, user_id=user_id, username=safe_account,
                category=cat, platform="x",
            )
            if not account:
                return {
                    "success": False,
                    "message": (
                        f"⚠️ ما لقيت حساب باسم '{safe_account}' في حساباتك.\n\n"
                        f"💡 اكتب 'اعرض حساباتي' للتأكد من اسم الحساب."
                    ),
                }

            ar, emoji = CATEGORY_LABELS[cat]
            return {
                "success": True,
                "message": (
                    f"✅ **تم تحديث تصنيف الحساب '{safe_account}'**\n\n"
                    f"📌 التصنيف الجديد: {emoji} **{ar}** ({cat})\n\n"
                    f"💡 لعرض الحسابات {ar}ة اكتب: `اعرض حساباتي ال{ar}ة`"
                ),
            }
        finally:
            db.close()
    except Exception as e:
        import traceback
        print(f"[x_set_account_category] {traceback.format_exc()}")
        return {"success": False, "message": f"❌ خطأ: {str(e)}"}


def x_list_accounts_by_category(category: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """يعرض حسابات المستخدم حسب التصنيف."""
    try:
        if not user_id:
            return {"success": False, "message": "⚠️ يجب تسجيل الدخول أولاً"}

        cat = (category or "").strip().lower()
        if cat and cat not in CATEGORY_LABELS:
            return {"success": False, "message": f"⚠️ تصنيف غير معروف: {category}"}

        from app.db.database import SessionLocal
        from app.services.account_service import account_service

        db = SessionLocal()
        try:
            accounts = account_service.get_user_accounts(
                db=db, user_id=user_id, platform="x",
                status="active", category=cat if cat else None,
            )

            if not accounts:
                if cat:
                    ar = CATEGORY_LABELS[cat][0]
                    return {
                        "success": True,
                        "message": (
                            f"📭 ما فيه حسابات مصنفة **{ar}** حالياً.\n\n"
                            f"💡 لتصنيف حساب اكتب: `غيّر تصنيف [اسم_الحساب] إلى {ar}`"
                        ),
                    }
                return {"success": True, "message": "📭 ما فيه حسابات نشطة"}

            ar_label = CATEGORY_LABELS[cat][0] if cat else "الكل"
            emoji = CATEGORY_LABELS[cat][1] if cat else "📋"

            lines = [f"{emoji} **حساباتك {ar_label}ة على X:**\n"]
            for i, acc in enumerate(accounts, 1):
                cat_display = _cat_label(acc.category)
                last_used = ""
                if acc.last_used:
                    last_used = f" (آخر استخدام: {acc.last_used.strftime('%Y-%m-%d')})"
                lines.append(f"{i}. 👤 **@{acc.username}** — {cat_display}{last_used}")

            lines.append(f"\n✅ **المجموع:** {len(accounts)} حساب")
            return {"success": True, "message": "\n".join(lines)}
        finally:
            db.close()
    except Exception as e:
        import traceback
        print(f"[x_list_accounts_by_category] {traceback.format_exc()}")
        return {"success": False, "message": f"❌ خطأ: {str(e)}"}


def _rewrite_content_for_account(content: str, account: Any) -> str:
    """
    يعيد صياغة المحتوى ليناسب أسلوب حساب معيّن (باستخدام OpenAI).
    يرجع النص الأصلي لو OpenAI مو متوفر.
    """
    try:
        from app.services.ai_service import ai_service
        import asyncio

        cat_display = _cat_label(account.category)
        account_desc = f"@{account.username}"
        if account.display_name and account.display_name != account.username:
            account_desc += f" ({account.display_name})"
        account_desc += f" — تصنيفه: {cat_display}"

        system_prompt = (
            "أنت مساعد إعادة صياغة تغريدات. تأخذ محتوى موحّد وتعيد صياغته "
            "ليناسب أسلوب وشخصية حساب معيّن، مع الحفاظ على المعنى الأصلي. "
            "اجعل النتيجة تغريدة واحدة قصيرة (تحت 280 حرف)، بدون علامات "
            "اقتباس ولا أي مقدمة."
        )
        user_prompt = (
            f"الحساب: {account_desc}\n\n"
            f"المحتوى الأصلي:\n{content}\n\n"
            f"أعد صياغته بأسلوب يناسب تصنيف الحساب:"
        )

        # نستدعي بشكل sync (نغلف الـ async)
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass

        if loop and loop.is_running():
            # داخل حلقة نشطة — نستخدم run_coroutine_threadsafe مو ممكن هنا،
            # فنرجع النص الأصلي كـ fallback
            return content

        result = asyncio.run(
            ai_service.get_chat_response_with_history(
                user_message=user_prompt,
                history=[],
                system_prompt=system_prompt,
            )
        )
        if result:
            return result.strip().strip('"').strip("'").strip("«»")
        return content
    except Exception as e:
        print(f"[_rewrite_content_for_account] {e}")
        return content


def x_post_to_category(category: str, content: str, user_id: Optional[int] = None, rewrite: bool = True) -> Dict[str, Any]:
    """
    ينشر محتوى موحّد على جميع حسابات المستخدم اللي في تصنيف معيّن.
    كل حساب يحصل على نسخة معاد صياغتها بأسلوبه (اختياري عبر OpenAI).
    """
    try:
        if not user_id:
            return {"success": False, "message": "⚠️ يجب تسجيل الدخول أولاً"}

        cat = (category or "").strip().lower()
        if cat not in CATEGORY_LABELS:
            return {"success": False, "message": f"⚠️ تصنيف غير معروف: {category}"}

        content = (content or "").strip()
        if not content:
            return {"success": False, "message": "⚠️ المحتوى فارغ"}

        from app.db.database import SessionLocal
        from app.services.account_service import account_service

        db = SessionLocal()
        try:
            accounts = account_service.get_user_accounts(
                db=db, user_id=user_id, platform="x",
                status="active", category=cat,
            )
        finally:
            db.close()

        ar = CATEGORY_LABELS[cat][0]
        if not accounts:
            return {
                "success": False,
                "message": (
                    f"📭 ما فيه حسابات مصنفة **{ar}** لنشر عليها.\n\n"
                    f"💡 صنّف حساب أولاً: `غيّر تصنيف [اسم_الحساب] إلى {ar}`"
                ),
            }

        # ننشر على كل حساب
        results = []
        for acc in accounts:
            try:
                # نعيد صياغة المحتوى (لو مطلوب)
                if rewrite:
                    tailored = _rewrite_content_for_account(content, acc)
                else:
                    tailored = content

                post_result = x_post(acc.username, tailored)
                results.append({
                    "account": acc.username,
                    "success": post_result.get("success", False),
                    "content": tailored[:100] + "..." if len(tailored) > 100 else tailored,
                    "message": post_result.get("message", ""),
                })
            except Exception as e:
                results.append({
                    "account": acc.username,
                    "success": False,
                    "content": content[:50],
                    "message": f"استثناء: {e}",
                })

        # نبني ردّ منظّم
        success_count = sum(1 for r in results if r["success"])
        total = len(results)

        lines = [
            f"📢 **نتيجة النشر على الحسابات {ar}ة:**",
            f"✅ نجح: **{success_count}** / **{total}**",
            "",
        ]
        for r in results:
            icon = "✅" if r["success"] else "❌"
            lines.append(f"{icon} **@{r['account']}**")
            lines.append(f"   📝 {r['content']}")
            if not r["success"]:
                lines.append(f"   ⚠️ {r['message']}")
            lines.append("")

        return {
            "success": success_count > 0,
            "message": "\n".join(lines),
            "results": results,
        }
    except Exception as e:
        import traceback
        print(f"[x_post_to_category] {traceback.format_exc()}")
        return {"success": False, "message": f"❌ خطأ: {str(e)}"}


def x_view_timeline(account_name: str, limit: int = 10, offset: int = 0, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    يعرض التغريدات المحفوظة من التايم لاين لحساب معين مرتّبة (الأحدث أولاً).

    Args:
        account_name: اسم الحساب
        limit: عدد التغريدات المعروضة (افتراضي 10)
        offset: تخطي عدد معين للتصفح (افتراضي 0)
    """
    try:
        from app.services.x_timeline_service import get_saved_tweets, count_saved_tweets
        safe_account = safe_label(account_name)
        if not safe_account:
            return {"success": False, "message": "⚠️ اسم الحساب فارغ"}

        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 10
        try:
            offset = int(offset)
        except (ValueError, TypeError):
            offset = 0
        limit = max(1, min(limit, 50))
        offset = max(0, offset)

        total = count_saved_tweets(safe_account, user_id=user_id)
        if total == 0:
            return {
                "success": True,
                "message": (
                    f"📭 ما فيه تغريدات محفوظة للحساب '{safe_account}' بعد.\n\n"
                    f"💡 لسحب التايم لاين اكتب: `اسحب التايم لاين حساب {safe_account}`"
                ),
            }

        tweets = get_saved_tweets(safe_account, limit=limit, offset=offset, user_id=user_id)
        if not tweets:
            return {
                "success": True,
                "message": f"📭 لا توجد تغريدات في هذه الصفحة (offset={offset}, total={total})",
            }

        # تنسيق العرض
        header = (
            f"📋 **تايم لاين الحساب '{safe_account}'** "
            f"(عرض {len(tweets)} من أصل {total})\n"
            f"{'─' * 40}\n"
        )
        lines = [header]

        for i, t in enumerate(tweets, start=offset + 1):
            text = (t.get("full_text") or "").strip()
            if len(text) > 280:
                text = text[:277] + "..."

            author = t.get("author_screen_name") or "?"
            author_name = t.get("author_name") or ""
            created = t.get("created_at") or ""
            likes = t.get("favorite_count", 0)
            rts = t.get("retweet_count", 0)
            replies = t.get("reply_count", 0)
            views = t.get("views_count", "0")
            url = t.get("tweet_url", "")

            # علامات النوع
            marks = []
            if t.get("is_retweet"):
                marks.append("🔁 RT")
            if t.get("is_reply"):
                marks.append("💬 رد")
            if t.get("is_quote"):
                marks.append("📌 اقتباس")
            if t.get("media_urls"):
                marks.append(f"📷 {len(t['media_urls'])} ميديا")

            marks_str = f" [{' · '.join(marks)}]" if marks else ""

            block = (
                f"\n**{i}. @{author}** {author_name}{marks_str}\n"
                f"{text}\n"
                f"📊 ❤️ {likes:,} · 🔁 {rts:,} · 💬 {replies:,} · 👁️ {views}\n"
                f"🕐 {created}\n"
            )
            if url:
                block += f"🔗 {url}\n"
            block += "─" * 40 + "\n"

            lines.append(block)

        # فوتر للتصفح
        if offset + len(tweets) < total:
            next_offset = offset + limit
            lines.append(
                f"\n📄 لعرض الأقدم اكتب: "
                f"`اعرض تغريدات {safe_account} تصفح {next_offset}`"
            )

        return {
            "success": True,
            "message": "".join(lines),
            "count": len(tweets),
            "total": total,
        }
    except Exception as e:
        import traceback
        print(f"[x_view_timeline] error: {traceback.format_exc()}")
        return {"success": False, "message": f"❌ خطأ أثناء عرض التغريدات: {str(e)}"}
