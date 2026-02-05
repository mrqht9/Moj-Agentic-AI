"""
API Client للتراجع عن الإعجاب
"""
import requests

API_URL = "http://localhost:5789"
API_TOKEN = "your-secure-token-here"


def undo_like(cookie_label: str, tweet_url: str, headless: bool = True) -> dict:
    """
    التراجع عن إعجاب تغريدة عبر API
    
    Args:
        cookie_label: اسم الكوكيز/الحساب
        tweet_url: رابط التغريدة
        headless: تشغيل المتصفح بدون واجهة
    
    Returns:
        dict: نتيجة العملية
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "cookie_label": cookie_label,
        "tweet_url": tweet_url,
        "headless": headless
    }
    
    response = requests.post(
        f"{API_URL}/api/undo-like",
        json=payload,
        headers=headers
    )
    
    return response.json()


if __name__ == "__main__":
    # مثال على الاستخدام
    COOKIE_LABEL = "myaccount"
    TWEET_URL = "https://x.com/user/status/1234567890123456789"
    
    print("جاري التراجع عن الإعجاب...")
    result = undo_like(
        cookie_label=COOKIE_LABEL,
        tweet_url=TWEET_URL,
        headless=False
    )
    print(result)
