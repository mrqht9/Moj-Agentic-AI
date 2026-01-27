import requests

url = "http://localhost:5789/api/quote"
headers = {"Authorization": "Bearer your-secure-token-here"}

data = {
    "cookie_label": "mualqahtani1",
    "tweet_url": "https://x.com/mualqahtani1/status/2016115522882986131",
    "text": "اقتباس من API ✅",
    "headless": False,
    "wait_after_ms": 3000
}

r = requests.post(url, headers=headers, json=data, timeout=6000)
print(r.status_code, r.text)
