#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rate Limiting Utilities
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    معالج مخصص لتجاوز حد الطلبات
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "too_many_requests",
            "message": "لقد تجاوزت الحد المسموح من الطلبات. يرجى المحاولة لاحقاً.",
            "detail": str(exc.detail)
        }
    )


# إنشاء limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # حد افتراضي: 100 طلب في الدقيقة
    storage_uri="memory://",  # استخدام الذاكرة للتخزين (يمكن استخدام Redis في الإنتاج)
)


# حدود مخصصة لـ endpoints مختلفة
RATE_LIMITS = {
    "auth_login": "5/minute",  # 5 محاولات تسجيل دخول في الدقيقة
    "auth_register": "3/hour",  # 3 تسجيلات في الساعة
    "post_create": "10/minute",  # 10 منشورات في الدقيقة
    "account_delete": "2/minute",  # حذف حسابين في الدقيقة
    "general": "30/minute",  # حد عام
}
