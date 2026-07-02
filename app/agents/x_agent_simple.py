#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وكيل X - نسخة مبسطة بدون autogen
"""

from typing import Dict, Any, Optional
import re
from .tools import (x_upload_cookies, x_post, x_update_profile, x_delete_account, x_delete_tweet,
                    x_like, x_repost, x_follow, x_unfollow, x_reply, x_bookmark, x_login_account,
                    x_login_status, x_fetch_timeline, x_view_timeline,
                    x_set_account_category, x_list_accounts_by_category, x_post_to_category)
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

    def _get_registered_x_accounts(self) -> list:
        """جلب قائمة labels الحسابات المسجّلة فعلاً في DB سيرفر app/x"""
        try:
            import sys
            from pathlib import Path
            x_dir = Path(__file__).parent.parent / "x"
            if str(x_dir) not in sys.path:
                sys.path.insert(0, str(x_dir))
            from modules.db import list_cookies
            cookies = list_cookies()
            return [c["label"] for c in cookies if c.get("label")]
        except Exception as e:
            print(f"[X_Agent] Failed to read x DB: {e}")
            # fallback لأسماء الملفات في المجلد
            try:
                from pathlib import Path
                cookies_dir = Path(__file__).parent.parent / "x" / "cookies"
                if cookies_dir.exists():
                    return [p.stem for p in cookies_dir.glob("*.json")]
            except Exception:
                pass
            return []

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
        # كلمات لا تصلح كأسماء حسابات
        _blacklist = {"https", "http", "الحساب", "حسابي", "حسابك", "default_account",
                      "جديد", "نشط", "قديم", "الجديد", "القديم",
                      "إلى", "الى", "الي", "to", "من", "في", "على",
                      "اسم", "إسم", "الاسم", "اسمي", "بايو", "البايو",
                      "هوية", "هويه", "الهوية", "بروفايل", "البروفايل",
                      "صورة", "الصورة", "غلاف", "الغلاف", "بانر", "البانر"}

        for pattern in account_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if candidate.lower() not in _blacklist:
                    return candidate
        
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

                    # تسجيل دخول عبر loginx API (نمرّر user_id من السياق
                    # عشان الحساب يتسجّل في DB ويظهر بـ "حساباتي" بعد نجاح الدخول)
                    mode_text = "مخفي" if headless else "ظاهر"
                    result = x_login_account(
                        username, password, email,
                        headless=headless, user_id=user_id,
                    )
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

        elif intent == "fetch_timeline":
            # سحب Home Timeline لحساب معين وحفظه في DB
            account = self._extract_account_name(message, entities, context)
            user_id = context.get("user_id") if context else None
            count = entities.get("count") or 50

            if account:
                account = sanitize_account_name(account)

            if not account or account == "default_account":
                return (
                    "⚠️ حدّد الحساب الذي تبي تسحب تايم لاينه\n\n"
                    "**أمثلة:**\n"
                    "• `اسحب التايم لاين حساب myuser`\n"
                    "• `جيب لي 100 تغريدة من حساب myuser`\n"
                    "• `حمل تغريدات من حساب myuser`"
                )

            result = x_fetch_timeline(account, count=count, user_id=user_id)
            return result.get("message", "حدث خطأ")

        elif intent == "view_timeline":
            # عرض التغريدات المحفوظة من التايم لاين
            account = self._extract_account_name(message, entities, context)
            user_id = context.get("user_id") if context else None
            limit = entities.get("limit") or 10
            offset = entities.get("offset") or 0

            if account:
                account = sanitize_account_name(account)

            if not account or account == "default_account":
                return (
                    "⚠️ حدّد الحساب الذي تبي تعرض تغريداته\n\n"
                    "**أمثلة:**\n"
                    "• `اعرض تغريدات حساب myuser`\n"
                    "• `اعرض 20 تغريدة من حساب myuser`\n"
                    "• `شوفلي تايم لاين حساب myuser`"
                )

            result = x_view_timeline(account, limit=limit, offset=offset, user_id=user_id)
            return result.get("message", "حدث خطأ")

        elif intent == "set_account_category":
            # غيّر تصنيف حساب معيّن
            user_id = context.get("user_id") if context else None
            account = self._extract_account_name(message, entities, context)
            category = entities.get("category")

            if account:
                account = sanitize_account_name(account)

            if not account or account == "default_account":
                return (
                    "⚠️ حدّد الحساب المطلوب تغيير تصنيفه\n\n"
                    "**مثال:** `غيّر تصنيف myuser إلى اجتماعي`"
                )

            if not category:
                return (
                    "⚠️ حدّد التصنيف الجديد\n\n"
                    "**التصنيفات:** اجتماعي / سياسي / رياضي / تقني / ديني / ترفيهي / إخباري / أدبي / تجاري / عام\n\n"
                    f"**مثال:** `غيّر تصنيف {account} إلى اجتماعي`"
                )

            result = x_set_account_category(account, category, user_id=user_id)
            return result.get("message", "حدث خطأ")

        elif intent == "list_accounts_by_category":
            # عرض الحسابات حسب التصنيف
            user_id = context.get("user_id") if context else None
            category = entities.get("category")

            if not category:
                return (
                    "⚠️ حدّد التصنيف الذي تريد عرضه\n\n"
                    "**أمثلة:**\n"
                    "• `اعرض حساباتي الاجتماعية`\n"
                    "• `اعرض الحسابات السياسية`\n"
                    "• `شوف حساباتي التقنية`"
                )

            result = x_list_accounts_by_category(category, user_id=user_id)
            return result.get("message", "حدث خطأ")

        elif intent == "post_to_category":
            # نشر جماعي على كل حسابات تصنيف معيّن
            user_id = context.get("user_id") if context else None
            category = entities.get("category")
            content = entities.get("content", "").strip()

            if not category:
                return (
                    "⚠️ حدّد التصنيف الذي تريد النشر عليه\n\n"
                    "**أمثلة:**\n"
                    "• `انشر في الحسابات الاجتماعية 'محتوى...'`\n"
                    "• `غرّد في حساباتي التقنية 'خبر تقني'`"
                )

            if not content:
                return (
                    f"⚠️ حدّد المحتوى المطلوب نشره\n\n"
                    f"**مثال:** `انشر في الحسابات {category} 'صباح الخير للجميع'`"
                )

            result = x_post_to_category(category, content, user_id=user_id, rewrite=True)
            return result.get("message", "حدث خطأ")
        
        elif intent == "update_profile":
            name = entities.get("name")
            bio = entities.get("bio")
            location = entities.get("location")
            website = entities.get("website")
            avatar_url = entities.get("avatar_url")
            banner_url = entities.get("banner_url")

            # تأكد أن في حقل واحد على الأقل يبي يتعدل
            if not any([name, bio, location, website, avatar_url, banner_url]):
                return (
                    "⚠️ ما حددت إيش تبي تعدل في الهوية.\n\n"
                    "💡 جرب مثلاً:\n"
                    "• \"عدّل بايو حسابي إلى 'مطور برمجيات'\"\n"
                    "• \"غيّر الاسم إلى 'أحمد' والبايو إلى 'كاتب محتوى'\"\n"
                    "• \"حدّث بروفايل حساب test_user: الاسم 'سارة' الموقع 'الرياض'\"\n"
                    "• \"غيّر صورة الحساب https://example.com/pic.jpg\"\n"
                    "• \"غيّر الغلاف https://example.com/banner.jpg\"\n\n"
                    "الحقول المدعومة: الاسم، البايو، الموقع، الرابط (الويبسايت)، الصورة، الغلاف"
                )

            # حدد اسم الحساب — أولاً من entities/الرسالة، ثم من DB سيرفر app/x
            account = self._extract_account_name(message, entities, context)
            if account:
                account = sanitize_account_name(account)

            # تحقق أن الحساب موجود في DB سيرفر app/x (وليس بس في ملفات الكوكيز)
            registered_labels = self._get_registered_x_accounts()

            if not account or account not in registered_labels:
                if not registered_labels:
                    return (
                        "⚠️ لا توجد حسابات X مسجّلة بعد.\n\n"
                        "💡 سجّل الدخول أولاً عبر:\n"
                        "• الواجهة على /x/login\n"
                        "• أو رفع كوكيز الحساب"
                    )

                accounts_list = "\n".join(f"• @{lbl}" for lbl in registered_labels)
                if not account:
                    return (
                        "⚠️ يرجى تحديد اسم الحساب اللي تبي تعدل هويته.\n\n"
                        f"📋 الحسابات المتاحة ({len(registered_labels)}):\n{accounts_list}\n\n"
                        "💡 مثال: \"غيّر صورة حساب " + registered_labels[0] + " https://...\""
                    )
                # account حُدّد لكن غير مسجّل
                return (
                    f"⚠️ الحساب \"@{account}\" غير مسجّل في النظام.\n\n"
                    f"📋 الحسابات المتاحة ({len(registered_labels)}):\n{accounts_list}\n\n"
                    "💡 استخدم اسماً من القائمة أعلاه."
                )

            # وضع المتصفح: من الـ entities أو من الكلمات في الرسالة
            headless = entities.get("headless")
            if headless is None:
                headless = not self._wants_visible(message)

            # تنفيذ
            print(f"[DEBUG] X_Agent: Updating profile for '{account}' "
                  f"(name={name}, bio={bio}, location={location}, "
                  f"website={website}, avatar={bool(avatar_url)}, "
                  f"banner={bool(banner_url)}, headless={headless})")

            result = x_update_profile(
                account,
                name=name,
                bio=bio,
                location=location,
                website=website,
                avatar_url=avatar_url,
                banner_url=banner_url,
                headless=headless,
            )

            if result.get("success"):
                changes = []
                if name: changes.append(f"الاسم → {name}")
                if bio: changes.append(f"البايو → {bio}")
                if location: changes.append(f"الموقع → {location}")
                if website: changes.append(f"الرابط → {website}")
                if avatar_url: changes.append("الصورة الشخصية ✓")
                if banner_url: changes.append("الغلاف ✓")
                changes_str = "\n• ".join(changes)
                return f"✅ تم تحديث هوية الحساب @{account} بنجاح\n\n• {changes_str}"

            return result.get("message", "⚠️ ما قدرت أحدث الملف الشخصي")
        
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

        elif intent == "schedule_post":
            return self._handle_schedule_post(message, entities, context)

        # إذا لم يتم التعرف على النية، لا ترجع شيء (دع الوكيل الرئيسي يتعامل معها)
        return None

    # ────────────────────────── جدولة التغريدات ──────────────────────────
    def _parse_schedule_time(self, schedule_entity: Dict[str, Any]):
        """تحويل entity الوقت إلى datetime مستقبلية بتوقيت UTC (naive)"""
        from datetime import datetime, timedelta, timezone
        if not schedule_entity:
            return None

        KSA = timezone(timedelta(hours=3))
        UTC = timezone.utc
        now_ksa = datetime.now(UTC).astimezone(KSA)

        t = schedule_entity.get("type")
        groups = schedule_entity.get("groups") or []

        try:
            if t == "hours_from_now" and groups:
                n = int(groups[0])
                return (now_ksa + timedelta(hours=n)).astimezone(UTC).replace(tzinfo=None)

            if t == "minutes_from_now" and groups:
                n = int(groups[0])
                return (now_ksa + timedelta(minutes=n)).astimezone(UTC).replace(tzinfo=None)

            if t == "days_from_now" and groups:
                n = int(groups[0])
                return (now_ksa + timedelta(days=n)).astimezone(UTC).replace(tzinfo=None)

            if t == "tomorrow":
                # غداً نفس الساعة الحالية
                target = now_ksa + timedelta(days=1)
                return target.astimezone(UTC).replace(tzinfo=None)

            if t == "day_after_tomorrow":
                target = now_ksa + timedelta(days=2)
                return target.astimezone(UTC).replace(tzinfo=None)

            if t == "at_hour" and groups:
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) >= 2 and str(groups[1]).isdigit() else 0
                # إذا فيه مؤشر مساء/م/pm، حوّل لـ 24h
                if len(groups) >= 3:
                    suffix = str(groups[-1]).lower()
                    if suffix in ("مساء", "مساءً", "م", "pm", "ليلاً") and hour < 12:
                        hour += 12
                    elif suffix in ("صباح", "صباحاً", "ص", "am") and hour == 12:
                        hour = 0
                target = now_ksa.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
                if target <= now_ksa:
                    target += timedelta(days=1)
                return target.astimezone(UTC).replace(tzinfo=None)

            if t == "hh_mm" and len(groups) >= 2:
                hour = int(groups[0])
                minute = int(groups[1])
                target = now_ksa.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
                if target <= now_ksa:
                    target += timedelta(days=1)
                return target.astimezone(UTC).replace(tzinfo=None)
        except (ValueError, TypeError, IndexError):
            return None

        return None

    def _extract_tweet_content(self, message: str, entities: Dict) -> str:
        """استخراج نص التغريدة المجدولة"""
        # أولاً: لو موجود في entities
        content = entities.get("content")
        if content:
            return content.strip()

        # ثانياً: ابحث عن نص بين علامات اقتباس
        m = re.search(r"['\"«](.+?)['\"»]", message)
        if m:
            return m.group(1).strip()

        # ثالثاً: استخرج النص بعد كلمة مفتاحية
        for kw in ["تغريدة", "تغريده", "منشور", "بوست", "غرد", "انشر", "اكتب",
                  "tweet", "post"]:
            if kw in message.lower():
                parts = re.split(rf"{kw}\s*[:\-]?\s*", message, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) > 1:
                    remaining = parts[1].strip()
                    # احذف الكلمات المتعلقة بالوقت أو الحساب
                    remaining = re.sub(
                        r"(?:بعد\s+\d+\s+(?:ساعة|ساعات|دقيقة|دقايق|يوم|أيام|ايام)|"
                        r"غدا?ً?|بكر[ةاه]|بكير|في\s*الساعة\s+\d+(?::\d+)?|"
                        r"الساعة\s+\d+(?::\d+)?|\d{1,2}:\d{2}|"
                        r"(?:في|على|من|ل)\s*حساب\s+\S+|"
                        r"@\w+)",
                        "", remaining, flags=re.IGNORECASE
                    ).strip()
                    remaining = re.sub(r"\s+", " ", remaining).strip(" .,،:-")
                    if remaining and len(remaining) >= 2:
                        return remaining
        return ""

    def _handle_schedule_post(self, message: str, entities: Dict, context: Dict) -> str:
        """معالجة طلب جدولة تغريدة"""
        from datetime import datetime, timedelta, timezone

        # 1) استخراج النص
        content = self._extract_tweet_content(message, entities)
        if not content:
            return (
                "⚠️ ما حددت نص التغريدة.\n\n"
                "💡 جرب مثلاً:\n"
                "• \"جدول تغريدة 'صباح الخير' بكرا الساعة 9\"\n"
                "• \"انشر بعد 3 ساعات 'تذكير للاجتماع'\"\n"
                "• \"اكتب تغريدة غداً: مرحباً بالجميع\""
            )

        # 2) استخراج الحساب والتحقق منه
        account = self._extract_account_name(message, entities, context)
        if account:
            account = sanitize_account_name(account)
        registered = self._get_registered_x_accounts()

        if not account or account not in registered:
            if not registered:
                return "⚠️ لا توجد حسابات X مسجّلة. سجّل الدخول أولاً."
            accounts_list = "\n".join(f"• @{lbl}" for lbl in registered)
            if not account:
                # استخدم أول حساب مسجّل كافتراضي
                account = registered[0]
                print(f"[X_Agent] No account specified, using default: @{account}")
            else:
                return (
                    f"⚠️ الحساب \"@{account}\" غير مسجّل.\n\n"
                    f"📋 الحسابات المتاحة ({len(registered)}):\n{accounts_list}"
                )

        # 3) استخراج الوقت
        schedule_time_entity = entities.get("schedule_time")
        run_at = self._parse_schedule_time(schedule_time_entity)
        # لو ما حدد وقت، الـ schedule_service يختار تلقائياً حسب محتوى التغريدة

        # 4) إنشاء الحدث في DB المحلية (للتتبع) + إرسال للسيرفر app/x للنشر التلقائي
        try:
            from app.db.database import SessionLocal
            from app.services.schedule_service import create_schedule_event
            from app.services import x_bridge

            conversation_id = (context or {}).get("conversation_id")
            user_id = (context or {}).get("user_id")

            db = SessionLocal()
            try:
                # احفظ في DB المحلي (للتتبع + بيانات الإشعار)
                event = create_schedule_event(
                    db=db,
                    platform="x",
                    username=account,
                    category="user_scheduled",
                    content=content,
                    run_at=run_at,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
                run_at_for_bridge = event.run_at  # نستخدم الوقت اللي اختاره الـ service

                # أرسل للسيرفر app/x ليتولى النشر التلقائي
                run_at_iso = run_at_for_bridge.strftime('%Y-%m-%d %H:%M:%S')
                # webhook لإشعار الشات بنتيجة النشر
                webhook_base = (context or {}).get("webhook_base") or "http://127.0.0.1:3000"
                callback_url = f"{webhook_base}/api/webhooks/schedule_callback"

                bridge_result = x_bridge.schedule_post(
                    event_id=event.schedule_event_id,
                    cookie_label=account,
                    content=content,
                    run_at=run_at_iso,
                    callback_url=callback_url,
                    callback_payload={
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                    },
                    max_attempts=3,
                )

                if not bridge_result.get("success"):
                    # فشل التسجيل في سيرفر النشر — احذف الحدث المحلي
                    db.delete(event)
                    db.commit()
                    err = bridge_result.get("message", bridge_result.get("error", "خطأ غير معروف"))
                    return f"⚠️ فشل تسجيل الجدولة في نظام النشر: {err}"

                # تنسيق الوقت بتوقيت السعودية للعرض
                KSA = timezone(timedelta(hours=3))
                run_at_ksa = event.run_at.replace(tzinfo=timezone.utc).astimezone(KSA)
                time_str = run_at_ksa.strftime("%Y-%m-%d %I:%M %p")

                response = (
                    f"✅ تم جدولة التغريدة في نظام النشر التلقائي\n\n"
                    f"📝 النص: {content[:100]}{'...' if len(content) > 100 else ''}\n"
                    f"👤 الحساب: @{account}\n"
                    f"🕐 وقت النشر: {time_str} (توقيت السعودية)\n"
                    f"🆔 معرف الجدولة: {event.schedule_event_id}\n"
                    f"🔁 محاولات إعادة النشر عند الفشل: 3 (بفواصل 1د/5د/15د)\n"
                    f"🔔 سيصلك إشعار في الشات عند النشر أو الفشل\n"
                )
                if run_at is None:
                    response += f"⚙️ تم اختيار الوقت تلقائياً حسب نوع المحتوى ({event.intent_time})\n"
                return response
            finally:
                db.close()
        except Exception as e:
            print(f"[X_Agent] Schedule error: {e}")
            import traceback
            traceback.print_exc()
            return f"⚠️ فشل جدولة التغريدة: {e}"
