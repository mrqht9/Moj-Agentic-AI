import requests

url = "http://localhost:5789/api/login"
headers = {"Authorization": "Bearer your-secure-token-here"}

data = {
    "label": "Ga6rsah",          # اسم الكوكيز اللي بيتحفظ (cookies/mualqahtani1.json)
    "username": "Ga6rsah",
    "password": "Mm8221809--",
    "headless": False                # خله False أول مرة (أفضل)
}

r = requests.post(url, headers=headers, json=data, timeout=1200)
print(r.status_code)
print(r.text)
