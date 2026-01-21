import requests

url = "http://localhost:5789/api/profile/update"
headers = {"Authorization": "Bearer your-secure-token-here"}

data = {
    "cookie_label": "",
    "name": "",
    "bio": "مرحبا",
    "location": "الرياض",
    "website": "https://google.com",
    "avatar_url": "https://tweetdelete.net/resources/wp-content/uploads/2024/04/craig-whitehead-lbekri_riMg-unsplash.jpg",
    "banner_url": "https://example.com/banner.jpg",
    "headless": "0",   # مهم: السيرفر يتحقق headless == '1'
}

r = requests.post(url, headers=headers, data=data, timeout=600)
print(r.status_code, r.text)
