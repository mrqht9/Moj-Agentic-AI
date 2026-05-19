#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وكيل X - نسخة مبسطة بدون autogen
"""

from typing import Dict, Any, Optional
import re
from .tools import (x_upload_cookies, x_post, x_update_profile, x_delete_account, x_delete_tweet,
                    x_like, x_repost, x_follow, x_unfollow, x_reply, x_bookmark, x_login_account,
                    x_login_status)
from app.utils.validators import sanitize_text, sanitize_username, sanitize_account_name


class XAgent:
    """وكيل X المبسط"""

    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config

    def _wants_visible(self, message: str) -> bool:
        """اكتشاف هل المستخدم يريد رؤية المتصفح أثناء العملية (headless=False)."""
        if not message:
            return False
        keywords = [
            r"بشكل\s*ظاهر", r"بشكل\s*مرئي", r"اظهر\s*المتصفح", r"أظهر\s*المتصفح",
            r"اشوف\s*العملي", r"أشوف\s*العملي", r"ابغى\s*اشوف", r"أبغى\s*أشوف",
            r"خل\s*اشوف", r"خلني\s*اشوف", r"شغّل.*ظاهر", r"بدون\s*اخفاء",
            r"بدون\s*إخفاء", r"ظاهرة", r"مرئية", r"visible", r"not\s*headless",
            r"no\s*headless", r"show\s*browser",
        ]
        for pat in keywords:
            if re.search(pat, message, re.IGNORECASE):
                return True
        return False

    def _extract_account_name(self, message: str, entities: Dict, context: Dict = None) -> str:
        """استخراج اسم الحساب من الرسالة"""
        # أولاً: تحقق من entities
        if entities.get("account_name"):
            return entities["account_name"]
        
        # ثانياً: ابحث في الرسالة عن اسم حساب محدد
        account_patterns = [
            r"من حساب\s+(\w+)",
            r"حساب\s+(\w+)",
            r"في حساب\s+(\w+)",
            r"على حساب\s+(\w+)",
            r"@(\w+)"
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # ثالثاً: استخدم قاعدة البيانات للحسابات النشطة (دائماً)
        user_id = context.get("user_id") if context else None
        if user_id:
            try:
                from app.db.database import SessionLocal
                from app.services.account_service import account_service
                
                db = SessionLocal()
                try:
                    accounts = account_service.get_user_accounts(
                        db=db,
                        user_id=user_id,
                        platform="x",
                        status="active"
                    )
                    if accounts and len(accounts) > 0:
                        # إرجاع أول حساب نشط
                        print(f"[DEBUG] Using active account from DB: {accounts[0].username}")
                        return accounts[0].username
                finally:
                    db.close()
            except Exception as e:
                print(f"[ERROR] Failed to get user accounts: {e}")
        
        # افتراضي: استخدم أول حساب متاح من ملفات الكوكيز
        from pathlib import Path
        cookies_dir = Path(__file__).parent.parent / "x" / "cookies"
        if cookies_dir.exists():
            cookie_files = list(cookies_dir.glob("*.json"))
            if cookie_files:
                print(f"[DEBUG] Using first cookie file: {cookie_files[0].stem}")
                return cookie_files[0].stem
        
        print("[DEBUG] No accounts found")
        return None
    
    def process_request(self, message: str, context: Dict[str, Any] = None) -> str:
        """معالجة طلب"""
        
        # تنظيف الرسالة من المحتوى الخبيث
        message = sanitize_text(message, max_length=1000, allow_arabic=True)
        
        intent = context.get("intent") if context else None
        entities = context.get("entities", {}) if context else {}
        
        # معالجة "حالة التسجيل" بشكل مباشر
        status_match = re.search(r'حالة\s*(?:التسجيل|تسجيل\s*الدخول|اللوقن)', message)
        if status_match:
            session_id_match = re.search(r'(api_\w+)', message)
            sid = session_id_match.group(1) if session_id_match else ""
            result = x_login_status(sid)
            return result.get("message", "لا توجد معلومات")
        
        if intent == "add_account":
            user_id = context.get("user_id") if context else None
            cookies_data = context.get("cookies_data") if context else None
            label = entities.get("account_name")
            
            # إذا تم إرفاق كوكيز (من ملف مرفوع أو من الرسالة)
            if cookies_data:
                if label:
                    label = sanitize_account_name(label)
                
                if not label:
                    label = context.get("cookie_filename", "account") if context else "account"
                    label = sanitize_account_name(label)
                
                result = x_upload_cookies(cookies_data, label, user_id=user_id)
                
                if result.get("success"):
                    return f"✅ تم حفظ كوكيز الحساب بنجاح!\n\n📝 اسم الحساب: {result.get('label', label)}\n\nيمكنك الآن استخدام هذا الحساب للنشر وإدارة المحتوى."
                else:
                    return f"❌ فشل حفظ الكوكيز\n\n{result.get('message', 'حدث خطأ غير متوقع')}"
            else:
                # حاول استخراج username و password من الرسالة
                username = entities.get("username")
                password = entities.get("password")
                email = entities.get("email", "")
                
                # أنماط استخراج: "سجل دخول user123 pass456" أو "اليوزر user الباسورد pass"
                if not username or not password:
                    login_patterns = [
                        r"(?:اليوزر|يوزر|username|user)\s*[:\s]\s*(\S+)\s+(?:الباسورد|باسورد|password|pass)\s*[:\s]\s*(\S+)",
                        r"(?:سجل\s*دخول|login|دخلني|سجل\s*لي|دخول|ادخل|سجل)\s+(?:الحساب|حسابي?|لحساب|account)\s+(\S+)\s+(?:الباسورد|باسورد|password|pass)\s*[:\s]*\s*(\S+)",
                        r"(?:سجل\s*دخول|login|دخلني|سجل\s*لي|دخول|ادخل|سجل)\s+(\S+)\s+(?:الباسورد|باسورد|password|pass)\s*[:\s]*\s*(\S+)",
                        r"(?:سجل\s*دخول|login)\s+(\S+)\s+(\S+)",
                        r"(?:دخول|ادخل|سجل)\s+(\S+)\s+(\S+)",
                    ]
                    for pattern in login_patterns:
                        match = re.search(pattern, message, re.IGNORECASE)
                        if match:
                            username = match.group(1)
                            password = match.group(2)
                            break
                
                if username and password:
                    # تحديد وضع المحاكي (مخفي/ظاهر) — افتراضياً ظاهر
                    headless = entities.get("headless", False)
                    
                    # تسجيل دخول عبر loginx API
                    mode_text = "مخفي" if headless else "ظاهر"
                    result = x_login_account(username, password, email, headless=headless)
                    return result.get("message", "حدث خطأ")
                else:
                    return (
                        "📝 **لتسجيل دخول حساب X:**\n\n"
                        "**الطريقة 1 — بالكردنشلز:**\n"
                        "اكتب: `سجل دخول username password`\n"
                        "أو: `اليوزر username الباسورد password`\n\n"
                        "**الطريقة 2 — بالكوكيز:**\n"
                        "📎 ارفق ملف كوكيز JSON عبر زر الملفات\n\n"
                        "اختر الطريقة المناسبة لك."
                    )
        
        elif intent == "create_post":
            content = entities.get("content")
            media_url = entities.get("media_url")
            account = self._extract_account_name(message, entities, context)
            
            # تنظيف المحتوى
            if content:
                # إزالة رابط الميديا من نص التغريدة إذا كان موجوداً
                if media_url and media_url in content:
                    content = content.replace(media_url, "").strip()
                content = sanitize_text(content, max_length=280, allow_arabic=True)
            if account:
                account = sanitize_account_name(account)
            
            if content:
                result = x_post(account, content, media_url=media_url)
                print(f"[DEBUG X_Agent] x_post result: {result}")
                
                if result.get("success"):
                    response = f"✅ تم نشر التغريدة بنجاح على حساب '{account}'\n\n📝 المحتوى: {content}"
                    
                    # أضف رابط التغريدة إذا موجود
                    tweet_url = result.get("tweet_url")
                    if not tweet_url:
                        # استخرج الرابط من الـ message إذا لم يكن في حقل منفصل
                        message = result.get("message", "")
                        url_match = re.search(r'https://x\.com/\w+/status/\d+', message)
                        if url_match:
                            tweet_url = url_match.group(0)
                    
                    if tweet_url:
                        response += f"\n\n🔗 رابط التغريدة: {tweet_url}"
                    
                    return response
                else:
                    error_msg = result.get('message', 'حدث خطأ غير متوقع')
                    
                    # رسالة خطأ ديناميكية تعرض الحساب الفعلي المستخدم
                    response = f"❌ فشل النشر من حساب '{account}'\n\n"
                    
                    # إذا كان الخطأ timeout أو مشكلة في العثور على العناصر
                    if "Timeout" in error_msg or "لم يتم العثور" in error_msg or "SideNav_NewTweet_Button" in error_msg:
                        response += f"💡 **السبب المحتمل:** الجلسة منتهية أو تغيرت واجهة X\n\n"
                        response += f"🔄 **الحل المقترح:**\n"
                        response += f"1. استخرج كوكيز جديدة للحساب '{account}' من المتصفح\n"
                        response += f"2. ارفق ملف الكوكيز (JSON) هنا وسيتم تحديث الحساب تلقائياً\n"
                        response += f"3. ثم حاول النشر مرة أخرى\n\n"
                        response += f"📋 **التفاصيل التقنية:**\n{error_msg}"
                    else:
                        response += f"📋 **تفاصيل الخطأ:**\n{error_msg}\n\n"
                        response += f"💡 **اقتراح:** تأكد من أن الحساب '{account}' مسجل دخول ونشط"
                    
                    return response
            else:
                return "⚠️ يرجى تقديم محتوى التغريدة\n\nمثال: انشر \"سبحان الله\""
        
        elif intent == "delete_post":
            tweet_id = entities.get("tweet_id")
            account = self._extract_account_name(message, entities, context)
            print(f"[DEBUG X_Agent] Extracted account: {account}, tweet_id: {tweet_id}")
            
            if account:
                account = sanitize_account_name(account)
                print(f"[DEBUG X_Agent] Sanitized account: {account}")
            
            if tweet_id:
                if not account:
                    return "⚠️ لم يتم العثور على حساب افتراضي\n\nيرجى تحديد الحساب:\nمثال: احذف من حساب djdkdkdysy 123456789012345678"
                
                print(f"[DEBUG X_Agent] Deleting tweet {tweet_id} from account {account}")
                result = x_delete_tweet(account, tweet_id)
                print(f"[DEBUG X_Agent] x_delete_tweet result: {result}")
                
                if result.get("success"):
                    return f"✅ تم حذف التغريدة بنجاح من حساب '{account}'\n\n📝 معرف التغريدة: {tweet_id}"
                else:
                    error_msg = result.get('message', 'حدث خطأ غير متوقع')
                    response = f"❌ فشل حذف التغريدة من حساب '{account}'\n\n"
                    response += f"📋 **تفاصيل الخطأ:**\n{error_msg}\n\n"
                    response += f"💡 **اقتراح:** تأكد من أن الحساب '{account}' مسجل دخول وأن التغريدة موجودة"
                    return response
            else:
                return "⚠️ يرجى تقديم معرف التغريدة\n\nمثال: احذف 123456789012345678"
        
        elif intent == "remove_account":
            # استخراج اسم الحساب
            account = self._extract_account_name(message, entities, context)
            user_id = context.get("user_id") if context else None
            
            # تنظيف اسم الحساب
            if account:
                account = sanitize_account_name(account)
            
            if account and account != "default_account":
                print(f"[DEBUG] X_Agent: Deleting account '{account}' for user_id={user_id}")
                result = x_delete_account(account, user_id=user_id)
                response_message = result.get("message", "تم محاولة حذف الحساب")
                print(f"[DEBUG] X_Agent: Delete result - success={result.get('success')}, message={response_message[:100] if response_message else 'None'}")
                return response_message
            else:
                return "⚠️ يرجى تحديد اسم الحساب المراد حذفه\n\nمثال: احذف حساب test_user"
        
        elif intent == "update_profile":
            account = entities.get("account_name", "default_account")
            name = entities.get("name")
            bio = entities.get("bio")
            
            result = x_update_profile(account, name=name, bio=bio)
            return result.get("message", "تم محاولة تحديث الملف الشخصي")
        
        elif intent == "like_post":
            tweet_url = entities.get("tweet_url")
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)
            if tweet_url:
                result = x_like(account, tweet_url)
                return result.get("message", "تم محاولة الإعجاب")
            else:
                return "⚠️ يرجى إرفاق رابط التغريدة\n\nمثال: لايك https://x.com/user/status/123456789"
        
        elif intent in ["repost", "share_post"]:
            tweet_url = entities.get("tweet_url")
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)
            if tweet_url:
                result = x_repost(account, tweet_url)
                return result.get("message", "تم محاولة إعادة النشر")
            else:
                return "⚠️ يرجى إرفاق رابط التغريدة\n\nمثال: أعد نشر https://x.com/user/status/123456789"
        
        elif intent == "follow_user":
            profile_url = entities.get("profile_url")
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)

            if not profile_url:
                # حاول بناء رابط من اسم المستخدم في الرسالة
                username_match = re.search(r'@(\w+)', message)
                if username_match:
                    profile_url = f"https://x.com/{username_match.group(1)}"

            if profile_url:
                headless = not self._wants_visible(message)
                result = x_follow(account, profile_url, headless=headless)
                return result.get("message", "تم محاولة المتابعة")
            else:
                return "⚠️ يرجى تحديد الحساب المراد متابعته\n\nمثال: تابع @username\nأو: تابع https://x.com/username"

        elif intent == "unfollow_user":
            profile_url = entities.get("profile_url")
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)

            if not profile_url:
                username_match = re.search(r'@(\w+)', message)
                if username_match:
                    profile_url = f"https://x.com/{username_match.group(1)}"

            if profile_url:
                headless = not self._wants_visible(message)
                result = x_unfollow(account, profile_url, headless=headless)
                return result.get("message", "تم محاولة إلغاء المتابعة")
            else:
                return "⚠️ يرجى تحديد الحساب\n\nمثال: ألغ متابعة @username"
        
        elif intent == "reply_to_comment":
            tweet_url = entities.get("tweet_url")
            reply_text = entities.get("reply_text")
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)
            
            if tweet_url and reply_text:
                result = x_reply(account, tweet_url, reply_text)
                return result.get("message", "تم محاولة الرد")
            elif not tweet_url:
                return "⚠️ يرجى إرفاق رابط التغريدة\n\nمثال: رد على https://x.com/user/status/123 \"نص الرد\""
            else:
                return "⚠️ يرجى كتابة نص الرد\n\nمثال: رد على https://x.com/user/status/123 \"نص الرد\""
        
        elif intent == "bookmark_post":
            tweet_url = entities.get("tweet_url")
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)
            if tweet_url:
                result = x_bookmark(account, tweet_url)
                return result.get("message", "تم محاولة الحفظ")
            else:
                return "⚠️ يرجى إرفاق رابط التغريدة\n\nمثال: احفظ تغريدة https://x.com/user/status/123456789"
        
        # إذا لم يتم التعرف على النية، لا ترجع شيء (دع الوكيل الرئيسي يتعامل معها)
        return None
