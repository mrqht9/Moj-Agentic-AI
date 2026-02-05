"""
مثال على حذف تغريدة عبر API
Delete Tweet API Client
"""

import requests

# إعدادات API
API_BASE_URL = "http://localhost:5789"
API_TOKEN = "your-secure-token-here"  # ضع التوكن الخاص بك هنا


def delete_tweet(cookie_label: str, tweet_id: str, headless: bool = True) -> dict:
    """
    حذف تغريدة عبر API.
    
    Args:
        cookie_label: اسم الحساب (الكوكيز)
        tweet_id: ID التغريدة
        headless: تشغيل بدون واجهة
    
    Returns:
        dict: استجابة API
    """
    url = f"{API_BASE_URL}/api/delete-tweet"
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "cookie_label": cookie_label,
        "tweet_id": tweet_id,
        "headless": headless
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


if __name__ == "__main__":
    # مثال على الاستخدام
    # غيّر القيم حسب حسابك
    
    COOKIE_LABEL = "mualqahtani1"       # اسم الكوكيز المحفوظ
    TWEET_ID = "2019370383254896652" # ID التغريدة المراد حذفها
    
    print("جاري حذف التغريدة...")
    result = delete_tweet(
        cookie_label=COOKIE_LABEL,
        tweet_id=TWEET_ID,
        headless=False  # False لرؤية المتصفح
    )
    
    print("النتيجة:")
    print(result)
    
    if result.get("success"):
        print("✅ تم حذف التغريدة بنجاح!")
    else:
        print(f"❌ فشل الحذف: {result.get('error')}")
