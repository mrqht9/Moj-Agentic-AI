"""
تسجيل الدخول في X — مستقل تماماً
بدون أي مكتبة خارجية غير المتطلبات الأساسية

الاستخدام:
    python x_login_standalone.py

المتطلبات:
    pip install curl_cffi stpyv8 beautifulsoup4 lxml chompjs mmh3
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import asyncio
from x_auth import x_login, x_login_multi


async def login_single():
    """تسجيل دخول حساب واحد"""
    username = input("اسم المستخدم: ").strip()
    password = input("كلمة المرور: ").strip()
    email = input("الإيميل (اختياري — اضغط Enter للتخطي): ").strip() or None

    cookies = await x_login(username, password, email)
    print(f"\nauth_token: {cookies.get('auth_token', '')[:30]}...")
    print(f"ct0: {cookies.get('ct0', '')[:30]}...")


async def login_multiple():
    """تسجيل دخول عدة حسابات"""
    accounts = []
    print("أدخل الحسابات (اكتب 'done' للبدء):\n")

    while True:
        username = input(f"  حساب #{len(accounts)+1} — اسم المستخدم (أو 'done'): ").strip()
        if username.lower() == 'done':
            break
        password = input(f"  حساب #{len(accounts)+1} — كلمة المرور: ").strip()
        email = input(f"  حساب #{len(accounts)+1} — الإيميل (اختياري): ").strip() or None
        accounts.append({"username": username, "password": password, "email": email})
        print()

    if not accounts:
        print("لم يتم إدخال أي حساب.")
        return

    results = await x_login_multi(accounts)
    return results


async def main():
    print("=" * 50)
    print("  X Login — مشروع مستقل")
    print("=" * 50)
    print()
    print("  1. تسجيل دخول حساب واحد")
    print("  2. تسجيل دخول عدة حسابات")
    print()

    choice = input("اختر (1 أو 2): ").strip()

    if choice == '1':
        await login_single()
    elif choice == '2':
        await login_multiple()
    else:
        print("اختيار غير صحيح")


if __name__ == "__main__":
    asyncio.run(main())
