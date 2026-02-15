"""
مولد الهويات - Remote Client
استخدم هذا الملف للاتصال بالـ API من أي جهاز باستخدام requests فقط

الاستخدام:
    python remote_client.py

المتطلبات:
    pip install requests
"""

import requests
import base64
import os
import uuid


# ============================================
# الإعدادات - غيّر هذا العنوان لعنوان السيرفر
# ============================================
SERVER_URL = "http://YOUR_SERVER_IP:5000"  # مثال: http://192.168.1.100:5000


def generate_identity(
    description: str,
    nationality: str = "سعودي",
    orientation: str = "عام",
    bio_length: str = "متوسط",
    bio_style: str = "فصحى",
    gender: str = "ذكر",
    skin_tone: str = "متوسط",
    include_images: bool = True
) -> dict:
    """
    توليد هوية كاملة
    
    Args:
        description: وصف الشخصية (مثال: "مبرمج سعودي")
        nationality: الجنسية
        orientation: توجه الحساب (تقني، ديني، رياضي، إلخ)
        bio_length: طول البايو (قصير، متوسط، طويل)
        bio_style: نمط البايو (فصحى، عامية، إنجليزي)
        gender: الجنس (ذكر، أنثى)
        skin_tone: لون البشرة
        include_images: توليد الصور (True/False)
        
    Returns:
        dict: بيانات الهوية الكاملة
    """
    
    # 1. توليد البيانات النصية
    print("جاري توليد البيانات النصية...")
    
    response = requests.post(
        f"{SERVER_URL}/api/profile/generate",
        json={
            "description": description,
            "nationality": nationality,
            "orientation": orientation,
            "bioLength": bio_length,
            "bioStyle": bio_style,
            "gender": gender,
            "skinTone": skin_tone
        },
        timeout=60
    )
    
    result = response.json()
    if not result.get("success"):
        raise Exception(f"فشل في توليد الملف الشخصي: {result.get('error')}")
    
    profile = result["data"]
    
    # 2. توليد الصور (اختياري)
    if include_images:
        print("جاري توليد الصور...")
        
        images_response = requests.post(
            f"{SERVER_URL}/api/image/generate-both",
            json={
                "profilePicPrompt": profile.get("profilePicPrompt", ""),
                "headerImagePrompt": profile.get("headerImagePrompt", "")
            },
            timeout=120
        )
        
        images_result = images_response.json()
        if images_result.get("success"):
            profile["profilePictureUrl"] = images_result["data"]["profilePictureUrl"]
            profile["headerImageUrl"] = images_result["data"]["headerImageUrl"]
            print("تم توليد الصور بنجاح!")
        else:
            print(f"تحذير: فشل في توليد الصور: {images_result.get('error')}")
    
    return profile


def generate_random_identity(include_images: bool = True) -> dict:
    """توليد هوية عشوائية"""
    
    print("جاري توليد هوية عشوائية...")
    
    response = requests.post(f"{SERVER_URL}/api/profile/random", timeout=60)
    result = response.json()
    
    if not result.get("success"):
        raise Exception(f"فشل في توليد الهوية: {result.get('error')}")
    
    profile = result["data"]
    
    if include_images:
        print("جاري توليد الصور...")
        
        images_response = requests.post(
            f"{SERVER_URL}/api/image/generate-both",
            json={
                "profilePicPrompt": profile.get("profilePicPrompt", ""),
                "headerImagePrompt": profile.get("headerImagePrompt", "")
            },
            timeout=120
        )
        
        images_result = images_response.json()
        if images_result.get("success"):
            profile["profilePictureUrl"] = images_result["data"]["profilePictureUrl"]
            profile["headerImageUrl"] = images_result["data"]["headerImageUrl"]
    
    return profile


def save_image(image_data: str, folder: str, filename: str = None) -> str:
    """
    حفظ صورة من base64 أو URL
    
    Args:
        image_data: بيانات الصورة (base64 أو URL)
        folder: اسم المجلد (profile_pictures أو header_pictures)
        filename: اسم الملف (اختياري - سيتم توليد اسم عشوائي)
        
    Returns:
        str: مسار الملف المحفوظ
    """
    if not image_data:
        return None
    
    # إنشاء المجلد
    os.makedirs(folder, exist_ok=True)
    
    # توليد اسم عشوائي
    if filename is None:
        filename = f"{uuid.uuid4().hex[:12]}.jpg"
    
    filepath = os.path.join(folder, filename)
    
    # حفظ الصورة
    if image_data.startswith("data:"):
        # base64
        header, data = image_data.split(",", 1)
        image_bytes = base64.b64decode(data)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
    else:
        # URL
        response = requests.get(image_data)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
    
    print(f"تم حفظ الصورة: {filepath}")
    return filepath


def regenerate_bio(
    description: str,
    nationality: str,
    orientation: str,
    bio_length: str,
    bio_style: str
) -> str:
    """إعادة توليد البايو فقط"""
    
    response = requests.post(
        f"{SERVER_URL}/api/bio/regenerate",
        json={
            "description": description,
            "nationality": nationality,
            "orientation": orientation,
            "bioLength": bio_length,
            "bioStyle": bio_style
        },
        timeout=60
    )
    
    result = response.json()
    if not result.get("success"):
        raise Exception(f"فشل في توليد البايو: {result.get('error')}")
    
    return result["data"]["bio"]


def regenerate_image(prompt: str, image_type: str = "profile") -> str:
    """
    توليد صورة واحدة
    
    Args:
        prompt: وصف الصورة
        image_type: نوع الصورة ('profile' أو 'header')
    """
    
    response = requests.post(
        f"{SERVER_URL}/api/image/generate",
        json={
            "prompt": prompt,
            "type": image_type
        },
        timeout=60
    )
    
    result = response.json()
    if not result.get("success"):
        raise Exception(f"فشل في توليد الصورة: {result.get('error')}")
    
    return result["data"]["imageUrl"]


# ============================================
# مثال على الاستخدام
# ============================================
if __name__ == "__main__":
    
    # تأكد من تغيير عنوان السيرفر!
    if "YOUR_SERVER_IP" in SERVER_URL:
        print("⚠️  تنبيه: غيّر SERVER_URL لعنوان السيرفر الخاص بك!")
        print("مثال: SERVER_URL = 'http://192.168.1.100:5000'")
        print()
        # للاختبار المحلي:
        SERVER_URL = "http://127.0.0.1:5000"
        print(f"استخدام العنوان المحلي للاختبار: {SERVER_URL}")
    
    print("=" * 50)
    print("مولد الهويات - Remote Client")
    print("=" * 50)
    
    try:
        # توليد هوية كاملة
        profile = generate_identity(
            description="مبرمج ومطور تطبيقات ذكاء اصطناعي",
            nationality="سعودي",
            orientation="تقني",
            bio_length="متوسط",
            bio_style="عامية",
            gender="ذكر",
            include_images=True
        )
        
        print("\n✅ تم توليد الهوية بنجاح!")
        print("-" * 40)
        print(f"الاسم: {profile.get('name')}")
        print(f"المعرف: {profile.get('username')}")
        print(f"البايو: {profile.get('bio')}")
        print(f"الموقع: {profile.get('location')}")
        print(f"الموقع الإلكتروني: {profile.get('website')}")
        print(f"تاريخ الميلاد: {profile.get('bornDate')}")
        print(f"تاريخ الانضمام: {profile.get('joinDate')}")
        print(f"المتابعون: {profile.get('followers')}")
        print(f"يتابع: {profile.get('following')}")
        
        # حفظ الصور
        print("\n📁 حفظ الصور...")
        
        profile_path = save_image(
            profile.get("profilePictureUrl"),
            "profile_pictures"
        )
        
        header_path = save_image(
            profile.get("headerImageUrl"),
            "header_pictures"
        )
        
        print(f"\nصورة الملف الشخصي: {profile_path}")
        print(f"صورة الغلاف: {header_path}")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ خطأ: لا يمكن الاتصال بالسيرفر على {SERVER_URL}")
        print("تأكد من أن السيرفر يعمل وأن العنوان صحيح")
    except Exception as e:
        print(f"❌ خطأ: {e}")
