#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Secure Logging Utilities - إخفاء البيانات الحساسة من logs
"""

import logging
import re
from typing import Any


class SecureFormatter(logging.Formatter):
    """
    Formatter مخصص لإخفاء البيانات الحساسة من logs
    """
    
    # أنماط البيانات الحساسة
    SENSITIVE_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'password=***'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'token=***'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'secret=***'),
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'api_key=***'),
        (r'Bearer\s+([A-Za-z0-9\-._~+/]+=*)', 'Bearer ***'),
        (r'user_id["\']?\s*[:=]\s*(\d+)', 'user_id=***'),
        (r'email["\']?\s*[:=]\s*["\']?([^"\'\s,}]+@[^"\'\s,}]+)', 'email=***@***'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """
        تنسيق السجل مع إخفاء البيانات الحساسة
        """
        # الحصول على الرسالة الأصلية
        original = super().format(record)
        
        # إخفاء البيانات الحساسة
        sanitized = original
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized


def get_secure_logger(name: str) -> logging.Logger:
    """
    إنشاء logger آمن مع إخفاء البيانات الحساسة
    
    Args:
        name: اسم الـ logger
    
    Returns:
        Logger مع formatter آمن
    """
    logger = logging.getLogger(name)
    
    # إذا كان الـ logger لديه handlers بالفعل، لا تضف جديدة
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # إنشاء console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # استخدام SecureFormatter
    formatter = SecureFormatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def sanitize_log_data(data: Any) -> Any:
    """
    تنظيف البيانات قبل logging
    
    Args:
        data: البيانات المراد تنظيفها
    
    Returns:
        البيانات المنظفة
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # إخفاء المفاتيح الحساسة
            if key.lower() in ['password', 'token', 'secret', 'api_key', 'credentials']:
                sanitized[key] = '***'
            elif key.lower() in ['user_id', 'email', 'username']:
                sanitized[key] = '***'
            else:
                sanitized[key] = sanitize_log_data(value)
        return sanitized
    
    elif isinstance(data, (list, tuple)):
        return [sanitize_log_data(item) for item in data]
    
    elif isinstance(data, str):
        # إخفاء أنماط حساسة في النصوص
        sanitized = data
        for pattern, replacement in SecureFormatter.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
    
    return data
