import requests

url = "http://localhost:5789/api/profile/update"
headers = {"Authorization": "Bearer your-secure-token-here"}

data = {
    "cookie_label": "mualqahtani1",
    "name": "mualqahtan5",
    "bio": "استغفر الله واتوب اليه",
    "location": "الرياض",
    "website": "https://google.com",
    "avatar_url": "https://pbs.twimg.com/media/EhsuMDLXkAA1tNm?format=jpg",
    "banner_url": "https://pbs.twimg.com/media/EymWxBwWgAERKcS?format=png",
    "headless": "0",   # مهم: السيرفر يتحقق headless == '1'
}

r = requests.post(url, headers=headers, data=data, timeout=600)
print(r.status_code, r.text)
