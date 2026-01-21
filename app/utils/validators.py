#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Input Validation and Sanitization Utilities
"""

import re
from html import escape
from typing import Optional


def sanitize_text(text: str, max_length: int = 500, allow_arabic: bool = True) -> str:
    """
    تنظيف النص من المحتوى الخبيث
    
    Args:
        text: النص المراد تنظيفه
        max_length: الحد الأقصى لطول النص
        allow_arabic: السماح بالأحرف العربية
    
    Returns:
        النص المنظف
    """
    if not text:
        return ""
    
    # إزالة HTML tags
    text = escape(text)
    
    # إزالة أحرف التحكم الخطرة
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # السماح فقط بأحرف آمنة
    if allow_arabic:
        # أحرف إنجليزية، عربية، أرقام، ومسافات وعلامات ترقيم أساسية
        pattern = r'[^\w\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF@._\-!?,;:\'\"\n]'
    else:
        # أحرف إنجليزية وأرقام فقط
        pattern = r'[^\w\s@._\-!?,;:\'\"\n]'
    
    text = re.sub(pattern, '', text)
    
    # تحديد الطول
    return text[:max_length]


def sanitize_username(username: str) -> str:
    """
    تنظيف اسم المستخدم
    
    Args:
        username: اسم المستخدم
    
    Returns:
        اسم المستخدم المنظف
    """
    if not username:
        return ""
    
    # السماح فقط بأحرف إنجليزية، أرقام، وشرطة سفلية
    username = re.sub(r'[^\w\-]', '', username)
    
    # تحديد الطول (3-50 حرف)
    return username[:50]


def sanitize_email(email: str) -> Optional[str]:
    """
    تنظيف والتحقق من صحة البريد الإلكتروني
    
    Args:
        email: البريد الإلكتروني
    
    Returns:
        البريد الإلكتروني المنظف أو None إذا كان غير صالح
    """
    if not email:
        return None
    
    # تنظيف أساسي
    email = email.strip().lower()
    
    # التحقق من صحة البريد الإلكتروني
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return None
    
    return email


def sanitize_url(url: str) -> Optional[str]:
    """
    تنظيف والتحقق من صحة الرابط
    
    Args:
        url: الرابط
    
    Returns:
        الرابط المنظف أو None إذا كان غير صالح
    """
    if not url:
        return None
    
    # التحقق من أن الرابط يبدأ بـ http أو https
    if not url.startswith(('http://', 'https://')):
        return None
    
    # التحقق من صحة الرابط
    url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    if not re.match(url_pattern, url):
        return None
    
    return url[:500]


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    التحقق من قوة كلمة المرور
    
    Args:
        password: كلمة المرور
    
    Returns:
        (صالحة أم لا، رسالة الخطأ)
    """
    if len(password) < 8:
        return False, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
    
    if len(password) > 128:
        return False, "كلمة المرور طويلة جداً"
    
    # يجب أن تحتوي على حرف كبير وصغير ورقم
    if not re.search(r'[a-z]', password):
        return False, "كلمة المرور يجب أن تحتوي على حرف صغير"
    
    if not re.search(r'[A-Z]', password):
        return False, "كلمة المرور يجب أن تحتوي على حرف كبير"
    
    if not re.search(r'\d', password):
        return False, "كلمة المرور يجب أن تحتوي على رقم"
    
    return True, ""


def sanitize_account_name(account_name: str) -> str:
    """
    تنظيف اسم الحساب (لحسابات X/Twitter)
    
    Args:
        account_name: اسم الحساب
    
    Returns:
        اسم الحساب المنظف
    """
    if not account_name:
        return ""
    
    # إزالة @ إذا كان موجوداً
    account_name = account_name.lstrip('@')
    
    # السماح فقط بأحرف إنجليزية، أرقام، وشرطة سفلية
    account_name = re.sub(r'[^\w]', '', account_name)
    
    return account_name[:50]


def is_safe_path(path: str) -> bool:
    """
    التحقق من أن المسار آمن (لا يحتوي على path traversal)
    
    Args:
        path: المسار
    
    Returns:
        True إذا كان آمناً
    """
    # منع path traversal attacks
    dangerous_patterns = ['..', '~', '/etc/', '/root/', 'C:\\', '\\\\']
    
    for pattern in dangerous_patterns:
        if pattern in path:
            return False
    
    return True
