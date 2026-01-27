import requests

url = "http://localhost:5789/api/bookmark"
headers = {"Authorization": "Bearer your-secure-token-here"}

data = {
    "cookie_label": "mualqahtani1",
    "tweet_url": "https://x.com/MaanAlquiae/status/2015890854934683868",
    "headless": False,
    "wait_after_ms": 3000
}

r = requests.post(url, headers=headers, json=data, timeout=600)
print(r.status_code, r.text)
