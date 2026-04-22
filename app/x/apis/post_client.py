import requests

url = "http://localhost:5789/api/post"
headers = {"Authorization": "Bearer your-secure-token-here"}

data = {
    "cookie_label": "djdkdkdysy",
    "text": "استغفر الله واتوب اليه العلي القدير66",
        #"media_url": "https://v2.jacocdn.com/v1/5071999642824580_1080p_30fps_h264_concat.mp4",
    "headless": False,
}

r = requests.post(url, headers=headers, json=data, timeout=600)
print(r.status_code, r.text)
