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
            return {"success": False, "message": f"❌ فشل إلغاء المتابعة: {result.get('error', 'خطأ')}"}
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
