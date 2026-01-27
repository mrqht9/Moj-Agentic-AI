#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
أدوات الوكلاء الذكية
Tools for AI Agents
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.utils.secure_logger import get_secure_logger

logger = get_secure_logger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.intent_service import intent_service
from app.x.modules.x_login import TwitterLoginAdvanced
from app.x.modules.x_post import post_to_x
from app.x.modules.x_profile import update_profile_on_x
from app.x.modules.utils import safe_label, download_to_temp, is_url
from app.agents.profile_agent import profile_agent

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


def _x_login_sync(username: str, password: str, label: str, headless: bool = False, user_id: Optional[int] = None) -> Dict[str, Any]:
    """تسجيل الدخول المتزامن (يعمل في thread منفصل)"""
    try:
        # استخدام username كاسم للملف بدلاً من label
        safe_username = safe_label(username)
        
        # تسجيل الدخول مباشرة
        engine = TwitterLoginAdvanced()
        cookie_path = engine.login_twitter(
            username=username,
            password=password,
            cookies_dir=str(COOKIES_DIR),
            headless=headless
        )
        
        # إعادة تسمية الملف باسم username
        dst = COOKIES_DIR / f"{safe_username}.json"
        cookie_filename = dst.name
        
        try:
            if Path(cookie_path).name != dst.name:
                Path(cookie_path).replace(dst)
        except Exception:
            pass
        
        # حفظ في قاعدة البيانات إذا كان user_id متوفراً
        if user_id:
            try:
                from app.db.database import SessionLocal
                from app.services.account_service import account_service
                from datetime import datetime
                
                print(f"[DEBUG] Attempting to save account to database: user_id={user_id}, username={username}")
                
                db = SessionLocal()
                try:
                    # تحقق إذا كان الحساب موجود
                    existing = account_service.get_account_by_username(
                        db=db,
                        user_id=user_id,
                        platform="x",
                        username=username
                    )
                    
                    if existing:
                        print(f"[DEBUG] Updating existing account: {existing.id}")
                        # تحديث الحساب الموجود
                        account_service.update_account(
                            db=db,
                            account_id=existing.id,
                            status="active",
                            last_login=datetime.utcnow(),
                            cookie_filename=cookie_filename,
                            error_message=None
                        )
                        print(f"[DEBUG] Account updated successfully")
                    else:
                        print(f"[DEBUG] Creating new account")
                        # إنشاء حساب جديد
                        new_account = account_service.create_account(
                            db=db,
                            user_id=user_id,
                            platform="x",
                            username=username,
                            display_name=username,
                            account_label=username,  # استخدام username بدلاً من label
                            cookie_filename=cookie_filename
                        )
                        print(f"[DEBUG] Account created successfully: {new_account.id}")
                finally:
                    db.close()
            except Exception as e:
                import traceback
                print(f"[ERROR] Failed to save account to database: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
        else:
            print(f"[WARNING] user_id is None, skipping database save")
        
        return {
            "success": True,
            "message": f"تم تسجيل الدخول بنجاح وحفظ الحساب باسم '{username}'",
            "label": username,
            "filename": cookie_filename
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"فشل تسجيل الدخول: {str(e)}"
        }


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


def x_login(username: str, password: str, label: str, headless: bool = False, user_id: Optional[int] = None) -> Dict[str, Any]:
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


def _x_post_sync(label: str, text: str, media_url: Optional[str] = None, headless: bool = False) -> Dict[str, Any]:
    """نشر تغريدة متزامن (يعمل في thread منفصل)"""
    try:
        label = safe_label(label)
        cookie_file = COOKIES_DIR / f"{label}.json"
        
        if not cookie_file.exists():
            # عرض الحسابات المتاحة
            available_accounts = []
            if COOKIES_DIR.exists():
                for f in COOKIES_DIR.glob("*.json"):
                    available_accounts.append(f.stem)
            
            error_msg = f"❌ الحساب '{label}' غير موجود.\n\n"
            
            if available_accounts:
                error_msg += f"📋 **الحسابات المتاحة:**\n"
                for acc in available_accounts:
                    error_msg += f"  • {acc}\n"
                error_msg += f"\n💡 **اقتراح:** استخدم أحد الحسابات المتاحة أو سجل دخول للحساب '{label}'"
            else:
                error_msg += f"⚠️ لا توجد حسابات محفوظة.\n\n"
                error_msg += f"💡 **الحل:** سجل دخول أولاً:\n"
                error_msg += f"```سجل دخول اليوزر {label} الباسورد [كلمة_المرور]```"
            
            return {
                "success": False,
                "message": error_msg
            }
        
        storage_state_path = str(cookie_file)
        
        # تحميل الميديا إذا كان هناك رابط
        with tempfile.TemporaryDirectory() as tmp:
            media_path = None
            if media_url and is_url(media_url):
                try:
                    media_path = download_to_temp(media_url, tmp)
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"فشل تنزيل الميديا: {str(e)}"
                    }
            
            # النشر مباشرة
            try:
                post_to_x(
                    storage_state_path=storage_state_path,
                    text=text,
                    media_path=media_path,
                    headless=headless
                )
                # إذا وصلنا هنا، النشر نجح
                return {
                    "success": True,
                    "message": f"تم نشر التغريدة بنجاح على حساب '{label}'"
                }
            except Exception as post_error:
                # النشر فشل
                error_msg = str(post_error)
                print(f"[ERROR] Post failed: {error_msg}")
                
                # رسالة خطأ واضحة
                if "الجلسة منتهية" in error_msg or "session expired" in error_msg.lower():
                    return {
                        "success": False,
                        "message": f"❌ فشل النشر من حساب '{label}'\n\n💡 **السبب:** الجلسة منتهية\n\n🔄 **الحل:**\n1. أعد تسجيل الدخول:\n   ```سجل دخول اليوزر {label} الباسورد [كلمة_المرور]```\n2. ثم حاول النشر مرة أخرى"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ فشل النشر من حساب '{label}'\n\n📋 **تفاصيل الخطأ:**\n{error_msg}"
                    }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"فشل النشر: {str(e)}"
        }


def x_post(label: str, text: str, media_url: Optional[str] = None, headless: bool = False) -> Dict[str, Any]:
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
    """تحديث الملف الشخصي متزامن (يعمل في thread منفصل)"""
    try:
        label = safe_label(label)
        cookie_file = COOKIES_DIR / f"{label}.json"
        
        if not cookie_file.exists():
            return {
                "success": False,
                "message": f"الحساب '{label}' غير موجود. يجب تسجيل الدخول أولاً."
            }
        
        storage_state_path = str(cookie_file)
        
        # تحميل الصور إذا كانت روابط
        with tempfile.TemporaryDirectory() as tmp:
            avatar_path = None
            banner_path = None
            
            if avatar_url and is_url(avatar_url):
                try:
                    avatar_path = download_to_temp(avatar_url, tmp)
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"فشل تنزيل الصورة الشخصية: {str(e)}"
                    }
            
            if banner_url and is_url(banner_url):
                try:
                    banner_path = download_to_temp(banner_url, tmp)
                except Exception as e:
                    return {
                        "success": False,
                        "message": f"فشل تنزيل صورة الغلاف: {str(e)}"
                    }
            
            # تحديث الملف الشخصي مباشرة
            update_profile_on_x(
                storage_state_path=storage_state_path,
                name=name,
                bio=bio,
                location=location,
                website=website,
                avatar_path=avatar_path,
                banner_path=banner_path,
                headless=headless
            )
        
        return {
            "success": True,
            "message": f"تم تحديث الملف الشخصي بنجاح لحساب '{label}'"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"فشل التحديث: {str(e)}"
        }


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


def generate_x_profile(niche: Optional[str] = None, style: str = "professional") -> Dict[str, Any]:
    """
    توليد هوية كاملة لحساب X باستخدام AI
    
    Args:
        niche: المجال أو التخصص (مثل: تقنية، رياضة، طبخ)
        style: نمط الهوية (professional, creative, casual)
        
    Returns:
        قاموس يحتوي على الهوية المولدة (name, bio, location, website)
    """
    try:
        profile = profile_agent.generate_complete_profile(niche=niche, style=style)
        return {
            "success": True,
            "profile": profile,
            "message": f"✅ تم توليد الهوية بنجاح!\n\n📝 **الاسم:** {profile['name']}\n💬 **البايو:** {profile['bio']}\n📍 **الموقع:** {profile.get('location', 'غير محدد')}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ فشل توليد الهوية: {str(e)}"
        }


def apply_generated_profile_to_x(
    label: str,
    profile: Dict[str, Any],
    headless: bool = False
) -> Dict[str, Any]:
    """
    تطبيق الهوية المولدة على حساب X
    
    Args:
        label: اسم الحساب المحفوظ
        profile: الهوية المولدة من generate_x_profile
        headless: تشغيل المتصفح في الخلفية
        
    Returns:
        نتيجة تطبيق الهوية
    """
    try:
        return x_update_profile(
            label=label,
            name=profile.get("name"),
            bio=profile.get("bio"),
            location=profile.get("location"),
            website=profile.get("website"),
            headless=headless
        )
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ فشل تطبيق الهوية: {str(e)}"
        }


def create_and_apply_x_profile(
    label: str,
    niche: Optional[str] = None,
    style: str = "professional",
    headless: bool = False
) -> Dict[str, Any]:
    """
    توليد وتطبيق هوية كاملة على حساب X في خطوة واحدة
    
    Args:
        label: اسم الحساب المحفوظ
        niche: المجال أو التخصص
        style: نمط الهوية
        headless: تشغيل المتصفح في الخلفية
        
    Returns:
        نتيجة العملية الكاملة
    """
    try:
        # 1. توليد الهوية
        print(f"[INFO] Generating profile for niche: {niche}")
        profile_result = generate_x_profile(niche=niche, style=style)
        
        if not profile_result["success"]:
            return profile_result
        
        profile = profile_result["profile"]
        
        # 2. تطبيق الهوية على الحساب
        print(f"[INFO] Applying profile to account: {label}")
        apply_result = apply_generated_profile_to_x(
            label=label,
            profile=profile,
            headless=headless
        )
        
        if apply_result["success"]:
            return {
                "success": True,
                "profile": profile,
                "message": f"✅ تم إنشاء وتطبيق الهوية بنجاح على حساب '{label}'!\n\n📝 **الاسم:** {profile['name']}\n💬 **البايو:** {profile['bio']}\n📍 **الموقع:** {profile.get('location', 'غير محدد')}"
            }
        else:
            return {
                "success": False,
                "profile": profile,
                "message": f"⚠️ تم توليد الهوية لكن فشل تطبيقها:\n\n{apply_result['message']}\n\n📝 **الهوية المولدة:**\n- الاسم: {profile['name']}\n- البايو: {profile['bio']}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ خطأ في العملية: {str(e)}"
        }


def process_profile_request(user_input: str) -> Dict[str, Any]:
    """
    معالجة طلب المستخدم المتعلق بالهوية
    
    Args:
        user_input: نص الطلب من المستخدم
        
    Returns:
        نتيجة المعالجة
    """
    try:
        return profile_agent.process_request(user_input)
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ خطأ في معالجة الطلب: {str(e)}"
        }
