#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وكيل X - نسخة مبسطة بدون autogen
"""

from typing import Dict, Any, Optional
import re
from .tools import x_login, x_post, x_update_profile, x_delete_account
from app.utils.validators import sanitize_text, sanitize_username, sanitize_account_name


class XAgent:
    """وكيل X المبسط"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
    
    def _extract_credentials(self, message: str) -> Dict[str, str]:
        """استخراج بيانات الاعتماد من الرسالة"""
        credentials = {}
        
        # البحث عن اليوزر
        username_patterns = [
            r"(?:اليوزر|يوزر|username|user|اسم المستخدم)[\s:]+(\S+)",
            r"(?:user|username)[\s:]+(\S+)",
        ]
        for pattern in username_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                credentials['username'] = match.group(1)
                break
        
        # البحث عن الباسورد
        password_patterns = [
            r"(?:الباسورد|باسورد|password|pass|كلمة المرور|كلمة السر)[\s:]+(\S+)",
            r"(?:password|pass)[\s:]+(\S+)",
        ]
        for pattern in password_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                credentials['password'] = match.group(1)
                break
        
        return credentials
    
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
        
        # ثالثاً: إذا قال "حسابي" أو "احذف حسابي"، استخدم قاعدة البيانات
        if "حسابي" in message or "حساباتي" in message:
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
                return cookie_files[0].stem
        
        return None
    
    def process_request(self, message: str, context: Dict[str, Any] = None) -> str:
        """معالجة طلب"""
        
        # تنظيف الرسالة من المحتوى الخبيث
        message = sanitize_text(message, max_length=1000, allow_arabic=True)
        
        intent = context.get("intent") if context else None
        entities = context.get("entities", {}) if context else {}
        
        if intent == "add_account":
            # محاولة استخراج البيانات من الرسالة مباشرة
            extracted = self._extract_credentials(message)
            
            username = entities.get("username") or extracted.get("username")
            password = entities.get("password") or extracted.get("password")
            label = entities.get("account_name") or extracted.get("username", "default_account")
            user_id = context.get("user_id") if context else None
            
            # تنظيف المدخلات
            if username:
                username = sanitize_username(username)
            if label:
                label = sanitize_account_name(label)
            
            if username and password:
                result = x_login(username, password, label, user_id=user_id)
                
                if result.get("success"):
                    return f"✅ تم تسجيل الدخول بنجاح!\n\n📝 الحساب: {label}\n👤 اسم المستخدم: {username}\n\nيمكنك الآن استخدام هذا الحساب للنشر وإدارة المحتوى."
                else:
                    return f"❌ فشل تسجيل الدخول\n\n{result.get('message', 'حدث خطأ غير متوقع')}"
            else:
                missing = []
                if not username:
                    missing.append("اسم المستخدم")
                if not password:
                    missing.append("كلمة المرور")
                return f"⚠️ يرجى تقديم: {', '.join(missing)}\n\nمثال: سجل دخول اليوزر test_user الباسورد pass123"
        
        elif intent == "create_post":
            content = entities.get("content")
            account = self._extract_account_name(message, entities, context)
            
            # تنظيف المحتوى
            if content:
                content = sanitize_text(content, max_length=280, allow_arabic=True)
            if account:
                account = sanitize_account_name(account)
            
            if content:
                result = x_post(account, content)
                
                if result.get("success"):
                    return f"✅ تم نشر التغريدة بنجاح على حساب '{account}'\n\n📝 المحتوى: {content}"
                else:
                    error_msg = result.get('message', 'حدث خطأ غير متوقع')
                    
                    # رسالة خطأ ديناميكية تعرض الحساب الفعلي المستخدم
                    response = f"❌ فشل النشر من حساب '{account}'\n\n"
                    
                    # إذا كان الخطأ timeout أو مشكلة في العثور على العناصر
                    if "Timeout" in error_msg or "لم يتم العثور" in error_msg or "SideNav_NewTweet_Button" in error_msg:
                        response += f"💡 **السبب المحتمل:** الجلسة منتهية أو تغيرت واجهة X\n\n"
                        response += f"🔄 **الحل المقترح:**\n"
                        response += f"1. أعد تسجيل الدخول للحساب '{account}':\n"
                        response += f"   ```سجل دخول اليوزر {account} الباسورد [كلمة_المرور]```\n"
                        response += f"2. ثم حاول النشر مرة أخرى\n\n"
                        response += f"📋 **التفاصيل التقنية:**\n{error_msg}"
                    else:
                        response += f"📋 **تفاصيل الخطأ:**\n{error_msg}\n\n"
                        response += f"💡 **اقتراح:** تأكد من أن الحساب '{account}' مسجل دخول ونشط"
                    
                    return response
            else:
                return "⚠️ يرجى تقديم محتوى التغريدة\n\nمثال: انشر \"سبحان الله\""
        
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
        
        # إذا لم يتم التعرف على النية، لا ترجع شيء (دع الوكيل الرئيسي يتعامل معها)
        return None
