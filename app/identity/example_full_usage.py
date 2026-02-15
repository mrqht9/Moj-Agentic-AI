"""
مثال شامل لاستخدام API مولد الهويات
يشمل جميع الخصائص والدوال المتاحة

المتطلبات:
    pip install requests

الاستخدام:
    1. شغّل السيرفر: python app.py
    2. شغّل هذا الملف: python example_full_usage.py
"""

import requests
import base64
import os
import uuid
import json
from datetime import datetime


# ============================================
# إعدادات السيرفر
# ============================================
SERVER_URL = "http://127.0.0.1:5000"  # غيّره لعنوان السيرفر الخاص بك


# ============================================
# الخيارات المتاحة
# ============================================

# الجنسيات المتاحة
NATIONALITIES = {
    "الخليج": ["سعودي", "إماراتي", "كويتي", "قطري", "بحريني", "عماني"],
    "الشام": ["سوري", "لبناني", "أردني", "فلسطيني"],
    "شمال أفريقيا": ["مصري", "ليبي", "تونسي", "جزائري", "مغربي"],
    "أخرى": ["عراقي", "يمني", "سوداني", "أمريكي", "بريطاني", "تركي"]
}

# التوجهات المتاحة
ORIENTATIONS = [
    "عام",      # حساب عام
    "تقني",     # برمجة وتقنية
    "ديني",     # محتوى ديني
    "رياضي",    # رياضة
    "فني",      # فن وإبداع
    "سياسي",    # سياسة
    "اقتصادي",  # اقتصاد ومال
    "تعليمي",   # تعليم
    "طبي",      # طب وصحة
    "ترفيهي"    # ترفيه
]

# أطوال البايو
BIO_LENGTHS = [
    "قصير",    # جملة أو جملتين
    "متوسط",   # 3-4 جمل
    "طويل"     # 5+ جمل
]

# أنماط البايو
BIO_STYLES = [
    "فصحى",           # عربي فصيح
    "عامية",          # لهجة عامية
    "عامي وإنجليزي",  # مزيج
    "إنجليزي",        # إنجليزي بالكامل
    "إيموجي فقط"      # إيموجي فقط 🔥
]

# الجنس
GENDERS = ["ذكر", "أنثى"]

# لون البشرة (للصور)
SKIN_TONES = ["فاتح", "متوسط", "داكن"]


# ============================================
# دوال مساعدة
# ============================================

def save_image(image_data: str, folder: str, filename: str = None) -> str:
    """حفظ صورة من base64 أو URL"""
    if not image_data:
        return None
    
    os.makedirs(folder, exist_ok=True)
    
    if filename is None:
        filename = f"{uuid.uuid4().hex[:12]}.jpg"
    
    filepath = os.path.join(folder, filename)
    
    if image_data.startswith("data:"):
        header, data = image_data.split(",", 1)
        image_bytes = base64.b64decode(data)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
    else:
        response = requests.get(image_data)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
    
    return filepath


def print_profile(profile: dict):
    """طباعة بيانات الهوية بشكل منسق"""
    print("\n" + "=" * 50)
    print("📋 بيانات الهوية")
    print("=" * 50)
    print(f"👤 الاسم: {profile.get('name', 'غير محدد')}")
    print(f"🔖 المعرف: {profile.get('username', 'غير محدد')}")
    print(f"📝 البايو: {profile.get('bio', 'غير محدد')}")
    print(f"📍 الموقع: {profile.get('location', 'غير محدد')}")
    print(f"🌐 الموقع الإلكتروني: {profile.get('website', 'غير محدد')}")
    print(f"🎂 تاريخ الميلاد: {profile.get('bornDate', 'غير محدد')}")
    print(f"📅 تاريخ الانضمام: {profile.get('joinDate', 'غير محدد')}")
    print(f"👥 المتابعون: {profile.get('followers', 0):,}")
    print(f"➡️ يتابع: {profile.get('following', 0):,}")
    print(f"🖼️ صورة الملف الشخصي: {'✅' if profile.get('profilePictureUrl') else '❌'}")
    print(f"🎨 صورة الغلاف: {'✅' if profile.get('headerImageUrl') else '❌'}")
    print("=" * 50)


# ============================================
# 1. توليد هوية كاملة مع جميع الخصائص
# ============================================

def example_full_identity():
    """مثال: توليد هوية كاملة مع جميع الخصائص"""
    
    print("\n" + "🔷" * 25)
    print("مثال 1: توليد هوية كاملة مع جميع الخصائص")
    print("🔷" * 25)
    
    # توليد البيانات النصية
    response = requests.post(
        f"{SERVER_URL}/api/profile/generate",
        json={
            "description": "مبرمج ومطور تطبيقات ذكاء اصطناعي متخصص في Python و Machine Learning",
            "nationality": "سعودي",
            "orientation": "تقني",
            "bioLength": "متوسط",
            "bioStyle": "عامية",
            "gender": "ذكر",
            "skinTone": "متوسط",
            "imageType": "واقعي",
            "headerImageType": "تجريدي"
        },
        timeout=60
    )
    
    result = response.json()
    if not result.get("success"):
        print(f"❌ خطأ: {result.get('error')}")
        return None
    
    profile = result["data"]
    
    # توليد الصور
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
    
    print_profile(profile)
    
    # حفظ الصور
    profile_path = save_image(profile.get("profilePictureUrl"), "profile_pictures")
    header_path = save_image(profile.get("headerImageUrl"), "header_pictures")
    
    print(f"\n📁 الصور المحفوظة:")
    print(f"   صورة الملف الشخصي: {profile_path}")
    print(f"   صورة الغلاف: {header_path}")
    
    return profile


# ============================================
# 2. توليد هوية عشوائية
# ============================================

def example_random_identity():
    """مثال: توليد هوية عشوائية"""
    
    print("\n" + "🔶" * 25)
    print("مثال 2: توليد هوية عشوائية")
    print("🔶" * 25)
    
    response = requests.post(f"{SERVER_URL}/api/profile/random", timeout=60)
    result = response.json()
    
    if not result.get("success"):
        print(f"❌ خطأ: {result.get('error')}")
        return None
    
    profile = result["data"]
    print_profile(profile)
    
    return profile


# ============================================
# 3. توليد هوية بدون صور (أسرع)
# ============================================

def example_text_only():
    """مثال: توليد بيانات نصية فقط بدون صور"""
    
    print("\n" + "🔹" * 25)
    print("مثال 3: توليد نص فقط (بدون صور)")
    print("🔹" * 25)
    
    response = requests.post(
        f"{SERVER_URL}/api/profile/generate",
        json={
            "description": "طبيب أسنان",
            "nationality": "إماراتي",
            "orientation": "طبي",
            "bioLength": "قصير",
            "bioStyle": "فصحى",
            "gender": "ذكر"
        },
        timeout=60
    )
    
    result = response.json()
    if result.get("success"):
        print_profile(result["data"])
        return result["data"]
    
    return None


# ============================================
# 4. توليد هوية أنثوية
# ============================================

def example_female_identity():
    """مثال: توليد هوية أنثوية"""
    
    print("\n" + "🔸" * 25)
    print("مثال 4: توليد هوية أنثوية")
    print("🔸" * 25)
    
    response = requests.post(
        f"{SERVER_URL}/api/profile/generate",
        json={
            "description": "مصممة جرافيك ومبدعة محتوى",
            "nationality": "سعودي",
            "orientation": "فني",
            "bioLength": "متوسط",
            "bioStyle": "عامي وإنجليزي",
            "gender": "أنثى",
            "skinTone": "فاتح"
        },
        timeout=60
    )
    
    result = response.json()
    if result.get("success"):
        profile = result["data"]
        
        # توليد الصور
        images_response = requests.post(
            f"{SERVER_URL}/api/image/generate-both",
            json={
                "profilePicPrompt": profile.get("profilePicPrompt", ""),
                "headerImagePrompt": profile.get("headerImagePrompt", "")
            },
            timeout=120
        )
        
        if images_response.json().get("success"):
            profile["profilePictureUrl"] = images_response.json()["data"]["profilePictureUrl"]
            profile["headerImageUrl"] = images_response.json()["data"]["headerImageUrl"]
        
        print_profile(profile)
        return profile
    
    return None


# ============================================
# 5. إعادة توليد البايو بأنماط مختلفة
# ============================================

def example_regenerate_bio():
    """مثال: إعادة توليد البايو بأنماط مختلفة"""
    
    print("\n" + "🔻" * 25)
    print("مثال 5: إعادة توليد البايو بأنماط مختلفة")
    print("🔻" * 25)
    
    styles = ["فصحى", "عامية", "إنجليزي", "إيموجي فقط"]
    
    for style in styles:
        response = requests.post(
            f"{SERVER_URL}/api/bio/regenerate",
            json={
                "description": "مبرمج",
                "nationality": "سعودي",
                "orientation": "تقني",
                "bioLength": "قصير",
                "bioStyle": style
            },
            timeout=60
        )
        
        result = response.json()
        if result.get("success"):
            print(f"\n📝 نمط [{style}]:")
            print(f"   {result['data']['bio']}")


# ============================================
# 6. توليد صورة واحدة فقط
# ============================================

def example_single_image():
    """مثال: توليد صورة واحدة"""
    
    print("\n" + "🔺" * 25)
    print("مثال 6: توليد صورة واحدة")
    print("🔺" * 25)
    
    # صورة ملف شخصي
    response = requests.post(
        f"{SERVER_URL}/api/image/generate",
        json={
            "prompt": "شاب سعودي محترف يرتدي ثوب أبيض، خلفية مكتب حديث، إضاءة احترافية",
            "type": "profile"
        },
        timeout=60
    )
    
    result = response.json()
    if result.get("success"):
        image_url = result["data"]["imageUrl"]
        filepath = save_image(image_url, "profile_pictures", "custom_profile.jpg")
        print(f"✅ تم حفظ صورة الملف الشخصي: {filepath}")
    
    # صورة غلاف
    response = requests.post(
        f"{SERVER_URL}/api/image/generate",
        json={
            "prompt": "خلفية تقنية مجردة بألوان زرقاء وبنفسجية، أكواد برمجية، ذكاء اصطناعي",
            "type": "header"
        },
        timeout=60
    )
    
    result = response.json()
    if result.get("success"):
        image_url = result["data"]["imageUrl"]
        filepath = save_image(image_url, "header_pictures", "custom_header.jpg")
        print(f"✅ تم حفظ صورة الغلاف: {filepath}")


# ============================================
# 7. توليد عدة هويات وحفظها في JSON
# ============================================

def example_batch_generation():
    """مثال: توليد عدة هويات وحفظها"""
    
    print("\n" + "🔳" * 25)
    print("مثال 7: توليد عدة هويات")
    print("🔳" * 25)
    
    personas = [
        {"description": "مبرمج", "nationality": "سعودي", "orientation": "تقني", "gender": "ذكر"},
        {"description": "طبيبة", "nationality": "مصري", "orientation": "طبي", "gender": "أنثى"},
        {"description": "رياضي", "nationality": "إماراتي", "orientation": "رياضي", "gender": "ذكر"},
    ]
    
    profiles = []
    
    for i, persona in enumerate(personas, 1):
        print(f"\nجاري توليد الهوية {i}/{len(personas)}...")
        
        response = requests.post(
            f"{SERVER_URL}/api/profile/generate",
            json={
                "description": persona["description"],
                "nationality": persona["nationality"],
                "orientation": persona["orientation"],
                "bioLength": "متوسط",
                "bioStyle": "عامية",
                "gender": persona["gender"]
            },
            timeout=60
        )
        
        result = response.json()
        if result.get("success"):
            profile = result["data"]
            profiles.append({
                "name": profile.get("name"),
                "username": profile.get("username"),
                "bio": profile.get("bio"),
                "location": profile.get("location"),
                "followers": profile.get("followers"),
                "following": profile.get("following")
            })
            print(f"   ✅ {profile.get('name')}")
    
    # حفظ في ملف JSON
    with open("generated_profiles.json", "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 تم حفظ {len(profiles)} هوية في: generated_profiles.json")
    
    return profiles


# ============================================
# 8. توليد هويات بجنسيات مختلفة
# ============================================

def example_different_nationalities():
    """مثال: توليد هويات بجنسيات مختلفة"""
    
    print("\n" + "🌍" * 25)
    print("مثال 8: هويات بجنسيات مختلفة")
    print("🌍" * 25)
    
    nationalities = ["سعودي", "مصري", "إماراتي", "أمريكي"]
    
    for nationality in nationalities:
        response = requests.post(
            f"{SERVER_URL}/api/profile/generate",
            json={
                "description": "مهندس برمجيات",
                "nationality": nationality,
                "orientation": "تقني",
                "bioLength": "قصير",
                "bioStyle": "عامية",
                "gender": "ذكر"
            },
            timeout=60
        )
        
        result = response.json()
        if result.get("success"):
            profile = result["data"]
            print(f"\n🏳️ جنسية [{nationality}]:")
            print(f"   الاسم: {profile.get('name')}")
            print(f"   الموقع: {profile.get('location')}")
            print(f"   البايو: {profile.get('bio')[:50]}...")


# ============================================
# 9. توليد هويات بتوجهات مختلفة
# ============================================

def example_different_orientations():
    """مثال: توليد هويات بتوجهات مختلفة"""
    
    print("\n" + "🎯" * 25)
    print("مثال 9: هويات بتوجهات مختلفة")
    print("🎯" * 25)
    
    orientations = ["تقني", "ديني", "رياضي", "فني"]
    
    for orientation in orientations:
        response = requests.post(
            f"{SERVER_URL}/api/profile/generate",
            json={
                "description": "شخص سعودي",
                "nationality": "سعودي",
                "orientation": orientation,
                "bioLength": "قصير",
                "bioStyle": "عامية",
                "gender": "ذكر"
            },
            timeout=60
        )
        
        result = response.json()
        if result.get("success"):
            profile = result["data"]
            print(f"\n🎯 توجه [{orientation}]:")
            print(f"   الاسم: {profile.get('name')}")
            print(f"   البايو: {profile.get('bio')[:60]}...")


# ============================================
# 10. استخدام جميع الـ Endpoints
# ============================================

def example_all_endpoints():
    """مثال: استخدام جميع الـ API Endpoints"""
    
    print("\n" + "📡" * 25)
    print("مثال 10: جميع الـ API Endpoints")
    print("📡" * 25)
    
    endpoints = {
        "POST /api/profile/generate": "توليد ملف شخصي",
        "POST /api/profile/random": "هوية عشوائية",
        "POST /api/image/generate-both": "توليد صورتين",
        "POST /api/image/generate": "توليد صورة واحدة",
        "POST /api/bio/regenerate": "إعادة توليد البايو",
        "POST /api/text/regenerate": "إعادة توليد النص"
    }
    
    print("\n📋 الـ Endpoints المتاحة:")
    for endpoint, description in endpoints.items():
        print(f"   {endpoint} → {description}")


# ============================================
# تشغيل جميع الأمثلة
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 مولد الهويات - أمثلة شاملة")
    print("=" * 60)
    print(f"السيرفر: {SERVER_URL}")
    print("=" * 60)
    
    try:
        # اختبار الاتصال
        response = requests.get(SERVER_URL, timeout=5)
        print("✅ السيرفر متصل!")
    except:
        print(f"❌ لا يمكن الاتصال بالسيرفر على {SERVER_URL}")
        print("تأكد من تشغيل السيرفر: python app.py")
        exit(1)
    
    # تشغيل الأمثلة
    print("\n" + "-" * 60)
    print("اختر المثال الذي تريد تشغيله:")
    print("-" * 60)
    print("1. توليد هوية كاملة مع جميع الخصائص")
    print("2. توليد هوية عشوائية")
    print("3. توليد نص فقط (بدون صور)")
    print("4. توليد هوية أنثوية")
    print("5. إعادة توليد البايو بأنماط مختلفة")
    print("6. توليد صورة واحدة")
    print("7. توليد عدة هويات وحفظها")
    print("8. هويات بجنسيات مختلفة")
    print("9. هويات بتوجهات مختلفة")
    print("10. عرض جميع الـ Endpoints")
    print("0. تشغيل جميع الأمثلة")
    print("-" * 60)
    
    choice = input("\nأدخل رقم المثال (0-10): ").strip()
    
    examples = {
        "1": example_full_identity,
        "2": example_random_identity,
        "3": example_text_only,
        "4": example_female_identity,
        "5": example_regenerate_bio,
        "6": example_single_image,
        "7": example_batch_generation,
        "8": example_different_nationalities,
        "9": example_different_orientations,
        "10": example_all_endpoints,
    }
    
    if choice == "0":
        # تشغيل جميع الأمثلة
        for func in examples.values():
            try:
                func()
            except Exception as e:
                print(f"❌ خطأ: {e}")
    elif choice in examples:
        try:
            examples[choice]()
        except Exception as e:
            print(f"❌ خطأ: {e}")
    else:
        print("اختيار غير صحيح!")
    
    print("\n" + "=" * 60)
    print("✅ انتهى!")
    print("=" * 60)
