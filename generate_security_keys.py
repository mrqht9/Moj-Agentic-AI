#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate Security Keys for .env file
"""

import secrets
from cryptography.fernet import Fernet

print("=" * 70)
print("🔐 توليد مفاتيح الأمان")
print("=" * 70)
print()

# Generate JWT Secret Key
jwt_secret = secrets.token_urlsafe(64)
print("1. JWT_SECRET_KEY:")
print(f"   {jwt_secret}")
print()

# Generate Encryption Key
encryption_key = Fernet.generate_key().decode()
print("2. ENCRYPTION_KEY:")
print(f"   {encryption_key}")
print()

print("=" * 70)
print("📝 تعليمات:")
print("=" * 70)
print()
print("1. انسخ المفاتيح أعلاه")
print("2. افتح ملف .env")
print("3. أضف أو حدّث السطور التالية:")
print()
print(f"JWT_SECRET_KEY={jwt_secret}")
print(f"ENCRYPTION_KEY={encryption_key}")
print()
print("4. احفظ الملف")
print("5. أعد تشغيل التطبيق")
print()
print("⚠️ تحذير: لا تشارك هذه المفاتيح مع أحد!")
print("=" * 70)
