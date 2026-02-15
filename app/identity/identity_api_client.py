"""
Identity Generator API Client
مكتبة Python لتوليد الهويات عبر API

الاستخدام:
    from identity_api_client import IdentityAPI
    
    api = IdentityAPI()
    profile = api.generate_full_identity(
        description="مبرمج سعودي",
        nationality="سعودي",
        orientation="تقني"
    )
    print(profile)
"""

import requests
import base64
import os
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class IdentityProfile:
    """بيانات الهوية المولدة"""
    name: str
    username: str
    bio: str
    location: str
    website: str
    born_date: str
    join_date: str
    followers: int
    following: int
    profile_picture_url: Optional[str] = None
    header_image_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'username': self.username,
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'born_date': self.born_date,
            'join_date': self.join_date,
            'followers': self.followers,
            'following': self.following,
            'profile_picture_url': self.profile_picture_url,
            'header_image_url': self.header_image_url
        }
    
    def save_profile_picture(self, filename: str = None, folder: str = "profile_pictures") -> str:
        """
        حفظ صورة الملف الشخصي في مجلد profile_pictures
        
        Args:
            filename: اسم الملف (اختياري - سيتم توليد اسم عشوائي إذا لم يُحدد)
            folder: اسم المجلد (افتراضي: profile_pictures)
            
        Returns:
            str: مسار الملف المحفوظ
        """
        if not self.profile_picture_url:
            return None
            
        # إنشاء المجلد إذا لم يكن موجوداً
        os.makedirs(folder, exist_ok=True)
        
        # توليد اسم عشوائي إذا لم يُحدد
        if filename is None:
            filename = f"{uuid.uuid4().hex[:12]}.jpg"
        
        filepath = os.path.join(folder, filename)
        
        if self.profile_picture_url.startswith('data:'):
            self._save_base64_image(self.profile_picture_url, filepath)
        else:
            self._download_image(self.profile_picture_url, filepath)
        
        return filepath
    
    def save_header_image(self, filename: str = None, folder: str = "header_pictures") -> str:
        """
        حفظ صورة الغلاف في مجلد header_pictures
        
        Args:
            filename: اسم الملف (اختياري - سيتم توليد اسم عشوائي إذا لم يُحدد)
            folder: اسم المجلد (افتراضي: header_pictures)
            
        Returns:
            str: مسار الملف المحفوظ
        """
        if not self.header_image_url:
            return None
            
        # إنشاء المجلد إذا لم يكن موجوداً
        os.makedirs(folder, exist_ok=True)
        
        # توليد اسم عشوائي إذا لم يُحدد
        if filename is None:
            filename = f"{uuid.uuid4().hex[:12]}.jpg"
        
        filepath = os.path.join(folder, filename)
        
        if self.header_image_url.startswith('data:'):
            self._save_base64_image(self.header_image_url, filepath)
        else:
            self._download_image(self.header_image_url, filepath)
        
        return filepath
    
    def save_all_images(self) -> dict:
        """
        حفظ جميع الصور (الملف الشخصي + الغلاف) بأسماء عشوائية
        
        Returns:
            dict: مسارات الصور المحفوظة
        """
        return {
            'profile_picture': self.save_profile_picture(),
            'header_image': self.save_header_image()
        }
    
    def _save_base64_image(self, data_url: str, filepath: str):
        """حفظ صورة base64"""
        header, data = data_url.split(',', 1)
        image_bytes = base64.b64decode(data)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        print(f"تم حفظ الصورة: {filepath}")
    
    def _download_image(self, url: str, filepath: str):
        """تحميل صورة من URL"""
        response = requests.get(url)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"تم حفظ الصورة: {filepath}")


class IdentityAPI:
    """
    API Client لتوليد الهويات
    
    الاستخدام:
        api = IdentityAPI(base_url="http://127.0.0.1:5000")
        
        # توليد هوية كاملة مع الصور
        profile = api.generate_full_identity(
            description="مبرمج ومطور تطبيقات",
            nationality="سعودي",
            orientation="تقني",
            bio_length="متوسط",
            bio_style="عامية"
        )
        
        # حفظ الصور
        profile.save_profile_picture("my_profile.jpg")
        profile.save_header_image("my_header.jpg")
    """
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def generate_text_profile(
        self,
        description: str,
        nationality: str = "سعودي",
        orientation: str = "عام",
        bio_length: str = "متوسط",
        bio_style: str = "فصحى",
        gender: str = "ذكر",
        skin_tone: str = "متوسط"
    ) -> Dict[str, Any]:
        """
        توليد بيانات الملف الشخصي النصية فقط (بدون صور)
        
        Args:
            description: وصف الشخصية (مثال: "مبرمج سعودي")
            nationality: الجنسية
            orientation: توجه الحساب (تقني، ديني، رياضي، إلخ)
            bio_length: طول البايو (قصير، متوسط، طويل)
            bio_style: نمط البايو (فصحى، عامية، إنجليزي)
            gender: الجنس (ذكر، أنثى)
            skin_tone: لون البشرة
            
        Returns:
            dict: بيانات الملف الشخصي
        """
        payload = {
            'description': description,
            'nationality': nationality,
            'orientation': orientation,
            'bioLength': bio_length,
            'bioStyle': bio_style,
            'gender': gender,
            'skinTone': skin_tone
        }
        
        response = self.session.post(
            f"{self.base_url}/api/profile/generate",
            json=payload
        )
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"فشل في توليد الملف الشخصي: {result.get('error')}")
        
        return result['data']
    
    def generate_images(
        self,
        profile_prompt: str,
        header_prompt: str
    ) -> Dict[str, str]:
        """
        توليد صور الملف الشخصي والغلاف
        
        Args:
            profile_prompt: وصف صورة الملف الشخصي
            header_prompt: وصف صورة الغلاف
            
        Returns:
            dict: URLs للصور (profilePictureUrl, headerImageUrl)
        """
        payload = {
            'profilePicPrompt': profile_prompt,
            'headerImagePrompt': header_prompt
        }
        
        response = self.session.post(
            f"{self.base_url}/api/image/generate-both",
            json=payload,
            timeout=120  # الصور قد تستغرق وقتاً
        )
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"فشل في توليد الصور: {result.get('error')}")
        
        return result['data']
    
    def generate_full_identity(
        self,
        description: str,
        nationality: str = "سعودي",
        orientation: str = "عام",
        bio_length: str = "متوسط",
        bio_style: str = "فصحى",
        gender: str = "ذكر",
        skin_tone: str = "متوسط",
        image_type: str = "واقعي",
        header_image_type: str = "تجريدي",
        include_images: bool = True
    ) -> IdentityProfile:
        """
        توليد هوية كاملة مع الصور
        
        Args:
            description: وصف الشخصية
            nationality: الجنسية
            orientation: توجه الحساب
            bio_length: طول البايو
            bio_style: نمط البايو
            gender: الجنس
            skin_tone: لون البشرة
            image_type: نوع صورة الملف الشخصي
            header_image_type: نوع صورة الغلاف
            include_images: توليد الصور (True/False)
            
        Returns:
            IdentityProfile: كائن يحتوي على جميع بيانات الهوية
        """
        # توليد البيانات النصية
        print("جاري توليد البيانات النصية...")
        text_data = self.generate_text_profile(
            description=description,
            nationality=nationality,
            orientation=orientation,
            bio_length=bio_length,
            bio_style=bio_style,
            gender=gender,
            skin_tone=skin_tone
        )
        
        profile = IdentityProfile(
            name=text_data.get('name', ''),
            username=text_data.get('username', ''),
            bio=text_data.get('bio', ''),
            location=text_data.get('location', ''),
            website=text_data.get('website', ''),
            born_date=text_data.get('bornDate', ''),
            join_date=text_data.get('joinDate', ''),
            followers=text_data.get('followers', 0),
            following=text_data.get('following', 0)
        )
        
        # توليد الصور
        if include_images:
            print("جاري توليد الصور...")
            try:
                images = self.generate_images(
                    profile_prompt=text_data.get('profilePicPrompt', f'Portrait of a {gender} from {nationality}'),
                    header_prompt=text_data.get('headerImagePrompt', f'{header_image_type} header image')
                )
                profile.profile_picture_url = images.get('profilePictureUrl')
                profile.header_image_url = images.get('headerImageUrl')
                print("تم توليد الصور بنجاح!")
            except Exception as e:
                print(f"تحذير: فشل في توليد الصور: {e}")
        
        return profile
    
    def generate_random_identity(self, include_images: bool = True) -> IdentityProfile:
        """
        توليد هوية عشوائية
        
        Args:
            include_images: توليد الصور (True/False)
            
        Returns:
            IdentityProfile: كائن يحتوي على جميع بيانات الهوية
        """
        print("جاري توليد هوية عشوائية...")
        
        response = self.session.post(f"{self.base_url}/api/profile/random")
        result = response.json()
        
        if not result.get('success'):
            raise Exception(f"فشل في توليد الهوية: {result.get('error')}")
        
        data = result['data']
        
        profile = IdentityProfile(
            name=data.get('name', ''),
            username=data.get('username', ''),
            bio=data.get('bio', ''),
            location=data.get('location', ''),
            website=data.get('website', ''),
            born_date=data.get('bornDate', ''),
            join_date=data.get('joinDate', ''),
            followers=data.get('followers', 0),
            following=data.get('following', 0)
        )
        
        if include_images:
            print("جاري توليد الصور...")
            try:
                images = self.generate_images(
                    profile_prompt=data.get('profilePicPrompt', 'Professional portrait'),
                    header_prompt=data.get('headerImagePrompt', 'Abstract header')
                )
                profile.profile_picture_url = images.get('profilePictureUrl')
                profile.header_image_url = images.get('headerImageUrl')
            except Exception as e:
                print(f"تحذير: فشل في توليد الصور: {e}")
        
        return profile
    
    def regenerate_bio(
        self,
        description: str,
        nationality: str,
        orientation: str,
        bio_length: str,
        bio_style: str
    ) -> str:
        """
        إعادة توليد البايو فقط
        
        Returns:
            str: البايو الجديد
        """
        payload = {
            'description': description,
            'nationality': nationality,
            'orientation': orientation,
            'bioLength': bio_length,
            'bioStyle': bio_style
        }
        
        response = self.session.post(
            f"{self.base_url}/api/bio/regenerate",
            json=payload
        )
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"فشل في توليد البايو: {result.get('error')}")
        
        return result['data']['bio']
    
    def regenerate_single_image(self, prompt: str, image_type: str = "profile") -> str:
        """
        إعادة توليد صورة واحدة
        
        Args:
            prompt: وصف الصورة
            image_type: نوع الصورة ('profile' أو 'header')
            
        Returns:
            str: URL الصورة (base64 أو رابط)
        """
        payload = {
            'prompt': prompt,
            'type': image_type
        }
        
        response = self.session.post(
            f"{self.base_url}/api/image/generate",
            json=payload,
            timeout=60
        )
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"فشل في توليد الصورة: {result.get('error')}")
        
        return result['data']['imageUrl']


# مثال على الاستخدام
if __name__ == "__main__":
    # إنشاء كائن API
    api = IdentityAPI(base_url="http://127.0.0.1:5990")
    
    print("=" * 50)
    print("مولد الهويات - Identity Generator API")
    print("=" * 50)
    
    # توليد هوية كاملة
    try:
        profile = api.generate_full_identity(
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
        print(f"الاسم: {profile.name}")
        print(f"المعرف: {profile.username}")
        print(f"البايو: {profile.bio}")
        print(f"الموقع: {profile.location}")
        print(f"الموقع الإلكتروني: {profile.website}")
        print(f"تاريخ الميلاد: {profile.born_date}")
        print(f"تاريخ الانضمام: {profile.join_date}")
        print(f"المتابعون: {profile.followers}")
        print(f"يتابع: {profile.following}")
        print(f"صورة الملف الشخصي: {'✅ موجودة' if profile.profile_picture_url else '❌ غير موجودة'}")
        print(f"صورة الغلاف: {'✅ موجودة' if profile.header_image_url else '❌ غير موجودة'}")
        
        # حفظ الصور في مجلدات منفصلة بأسماء عشوائية
        print("\n📁 حفظ الصور...")
        saved_files = profile.save_all_images()
        print(f"صورة الملف الشخصي: {saved_files['profile_picture']}")
        print(f"صورة الغلاف: {saved_files['header_image']}")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
