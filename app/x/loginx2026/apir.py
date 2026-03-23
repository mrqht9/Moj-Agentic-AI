import requests

BASE = "http://127.0.0.1:5000"

# تسجيل دخول
r = requests.post(f"{BASE}/api/login", json={
    "username": "djdkdkdysy",
    "password": "SXWqWpc9FK"
})
print(r.json())

# جلب كوكيز
r = requests.get(f"{BASE}/api/cookies/user123")
data = r.json()
