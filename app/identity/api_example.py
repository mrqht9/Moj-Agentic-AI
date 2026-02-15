import requests
import json

BASE_URL = "http://127.0.0.1:51998"

print("جاري توليد الهوية الكاملة...")

# 1. توليد البيانات النصية + prompts الصور
response = requests.post(
    BASE_URL + "/api/profile/generate",
    json={
        "description": "ضابط",
        "nationality": "سعودي",
        "orientation": "عسكري",
        "bioLength": "متوسط",
        "bioStyle": "عامية",
        "gender": "رجل",
        "skinTone": "حنطي",
        "imageType": "شخص",
        "headerImageType": "تجريدي"
    },
    timeout=60
)

data = response.json()
if not data["success"]:
    print("خطأ: " + data.get("error", "غير معروف"))
    exit()

profile = data["data"]

# 2. توليد الصور (ملف شخصي + غلاف)
print("جاري توليد الصور...")
images_response = requests.post(
    BASE_URL + "/api/image/generate-both",
    json={
        "profilePicPrompt": profile.get("profilePicPrompt", ""),
        "headerImagePrompt": profile.get("headerImagePrompt", "")
    },
    timeout=120
)

images = images_response.json()
if images["success"]:
    profile["profilePictureUrl"] = images["data"]["profilePictureUrl"]
    profile["headerImageUrl"] = images["data"]["headerImageUrl"]

# 3. طباعة النتائج
print()
print("=" * 50)
print("الهوية الكاملة")
print("=" * 50)
print("الاسم: " + str(profile.get("name", "")))
print("المعرف: " + str(profile.get("username", "")))
print("البايو: " + str(profile.get("bio", "")))
print("الموقع: " + str(profile.get("location", "")))
print("الموقع الإلكتروني: " + str(profile.get("website", "")))
print("تاريخ الميلاد: " + str(profile.get("bornDate", "")))
print("تاريخ الانضمام: " + str(profile.get("joinDate", "")))
print("المتابعون: " + str(profile.get("followers", 0)))
print("يتابع: " + str(profile.get("following", 0)))

profile_pic = str(profile.get("profilePictureUrl", ""))
header_img = str(profile.get("headerImageUrl", ""))
print("صورة الملف الشخصي: " + profile_pic)
print("صورة الغلاف: " + header_img)
print("=" * 50)

# 4. حفظ كل شيء في ملف JSON
with open("my_identity.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, ensure_ascii=False, indent=2)

print("تم حفظ الهوية في: my_identity.json")
print("تم بنجاح!")
