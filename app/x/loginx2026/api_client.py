"""
X Login API Client
==================
كود بايثون لتسجيل الدخول عبر إرسال طلبات requests لرابط السيرفر

الاستخدام:
    1. شغّل السيرفر: python api_server.py
    2. شغّل هذا الملف: python api_client.py
"""
import requests
import time

# رابط المشروع (السيرفر)
BASE_URL = "http://127.0.0.1:8000"


# ============================================================
#  تسجيل دخول حساب واحد
# ============================================================
print("=" * 50)
print("  تسجيل دخول X عبر API")
print("=" * 50)

username = input("اسم المستخدم: ").strip()
password = input("كلمة المرور: ").strip()

if not username or not password:
    print("[✗] أدخل اسم المستخدم وكلمة المرور")
    exit(1)

print(f"\n[*] جاري تسجيل دخول @{username}...")

response = requests.post(
    f"{BASE_URL}/api/login",
    json={"username": username, "password": password}
)

result = response.json()

if result.get("success"):
    print(f"[✓] تم تسجيل الدخول بنجاح!")
    print(f"    ملف الكوكيز: {result.get('cookies_file', 'cookies/')}")

    # جلب الكوكيز
    cookies_resp = requests.get(f"{BASE_URL}/api/cookies/{username}")
    if cookies_resp.status_code == 200:
        cookies = cookies_resp.json()
        print(f"    auth_token: {cookies['auth_token'][:20]}...")
        print(f"    ct0: {cookies['ct0'][:20]}...")
else:
    print(f"[✗] فشل: {result.get('error', 'خطأ غير معروف')}")
