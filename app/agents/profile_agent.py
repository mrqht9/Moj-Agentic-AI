#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وكيل إدارة هوية حسابات X
X Profile Management Agent

هذا الوكيل مسؤول عن:
1. توليد هوية كاملة للحساب (اسم، بايو، موقع، إلخ)
2. استخدام Google Gemini لتوليد محتوى إبداعي
3. استخدام GPT لتحسين وصقل المحتوى
4. التنسيق مع وكيل X لتطبيق التعديلات
"""

import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from pathlib import Path
import google.generativeai as genai
from openai import OpenAI

# تحميل المتغيرات البيئية
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# إعداد Google Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# إعداد OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


class ProfileAgent:
    """وكيل إدارة الهوية لحسابات X"""
    
    def __init__(self):
        self.gemini_model = None
        if GOOGLE_API_KEY:
            try:
                self.gemini_model = genai.GenerativeModel('gemini-pro')
            except Exception as e:
                print(f"[WARNING] Failed to initialize Gemini: {e}")
        
        self.openai_client = openai_client
        
    def detect_intent(self, user_input: str) -> Dict[str, Any]:
        """
        تحليل نية المستخدم من النص
        
        Args:
            user_input: نص المستخدم
            
        Returns:
            قاموس يحتوي على النية والكيانات المستخرجة
        """
        user_input_lower = user_input.lower()
        
        # كلمات مفتاحية لإنشاء هوية
        create_keywords = [
            "أنشئ هوية", "إنشاء هوية", "هوية جديدة", "اصنع هوية",
            "create profile", "new profile", "generate profile",
            "عدل الهوية", "تعديل الهوية", "غير الهوية", "حدث الهوية"
        ]
        
        # كلمات مفتاحية لتوليد اسم
        name_keywords = [
            "اسم", "name", "توليد اسم", "generate name", "اقترح اسم"
        ]
        
        # كلمات مفتاحية لتوليد بايو
        bio_keywords = [
            "بايو", "bio", "نبذة", "وصف", "description", "about"
        ]
        
        # استخراج اسم الحساب
        account_name = None
        if "حساب" in user_input or "account" in user_input:
            words = user_input.split()
            for i, word in enumerate(words):
                if word in ["حساب", "account", "بحساب", "للحساب"]:
                    if i + 1 < len(words):
                        account_name = words[i + 1].strip(".,!?؛،")
        
        # استخراج المجال/النيش
        niche = None
        niche_keywords = ["مجال", "نيش", "niche", "تخصص", "موضوع", "عن"]
        for keyword in niche_keywords:
            if keyword in user_input_lower:
                words = user_input.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        if i + 1 < len(words):
                            niche = " ".join(words[i + 1:i + 4])
                            break
        
        # تحديد النية
        intent = "unknown"
        if any(keyword in user_input_lower for keyword in create_keywords):
            intent = "create_profile"
        elif any(keyword in user_input_lower for keyword in name_keywords):
            intent = "generate_name"
        elif any(keyword in user_input_lower for keyword in bio_keywords):
            intent = "generate_bio"
        
        return {
            "intent": intent,
            "account_name": account_name,
            "niche": niche,
            "original_text": user_input
        }
    
    def generate_name_with_gemini(self, niche: Optional[str] = None, style: str = "professional") -> str:
        """
        توليد اسم باستخدام Google Gemini
        
        Args:
            niche: المجال أو التخصص
            style: نمط الاسم (professional, creative, casual)
            
        Returns:
            اسم مقترح
        """
        if not self.gemini_model:
            return self._generate_name_fallback(niche, style)
        
        try:
            niche_text = f"في مجال {niche}" if niche else "عام"
            
            prompt = f"""أنت خبير في إنشاء أسماء احترافية لحسابات التواصل الاجتماعي.

المطلوب: توليد اسم {style} لحساب X (تويتر) {niche_text}

المتطلبات:
- الاسم يجب أن يكون جذاب ومميز
- مناسب للمجال المحدد
- سهل التذكر والنطق
- يعكس الاحترافية

قدم اسم واحد فقط بدون شرح أو تفاصيل إضافية."""

            response = self.gemini_model.generate_content(prompt)
            name = response.text.strip()
            
            # تنظيف الاسم
            name = name.replace('"', '').replace("'", '').strip()
            
            return name
            
        except Exception as e:
            print(f"[ERROR] Gemini name generation failed: {e}")
            return self._generate_name_fallback(niche, style)
    
    def generate_bio_with_gemini(self, name: str, niche: Optional[str] = None, tone: str = "professional") -> str:
        """
        توليد بايو باستخدام Google Gemini
        
        Args:
            name: اسم الحساب
            niche: المجال أو التخصص
            tone: نبرة البايو (professional, friendly, inspiring)
            
        Returns:
            نص البايو
        """
        if not self.gemini_model:
            return self._generate_bio_fallback(name, niche, tone)
        
        try:
            niche_text = f"متخصص في {niche}" if niche else "محتوى متنوع"
            
            prompt = f"""أنت خبير في كتابة نبذات تعريفية (Bio) احترافية لحسابات X (تويتر).

المطلوب: كتابة بايو {tone} لحساب باسم "{name}" - {niche_text}

المتطلبات:
- البايو يجب أن يكون مختصر (أقل من 160 حرف)
- جذاب ويعكس الشخصية
- يحتوي على كلمات مفتاحية مناسبة
- يشجع المتابعة
- يمكن إضافة إيموجي واحد أو اثنين مناسبين

قدم البايو فقط بدون شرح أو عناوين."""

            response = self.gemini_model.generate_content(prompt)
            bio = response.text.strip()
            
            # تنظيف البايو
            bio = bio.replace('"', '').replace("'", '').strip()
            
            # التأكد من الطول
            if len(bio) > 160:
                bio = bio[:157] + "..."
            
            return bio
            
        except Exception as e:
            print(f"[ERROR] Gemini bio generation failed: {e}")
            return self._generate_bio_fallback(name, niche, tone)
    
    def refine_with_gpt(self, content: str, content_type: str = "bio") -> str:
        """
        تحسين المحتوى باستخدام GPT
        
        Args:
            content: المحتوى المراد تحسينه
            content_type: نوع المحتوى (name, bio, location)
            
        Returns:
            المحتوى المحسّن
        """
        if not self.openai_client:
            return content
        
        try:
            if content_type == "bio":
                prompt = f"""حسّن هذا البايو لحساب X ليكون أكثر جاذبية واحترافية:

"{content}"

المتطلبات:
- يجب أن يكون أقل من 160 حرف
- احتفظ بالمعنى الأساسي
- اجعله أكثر تأثيراً
- يمكن إضافة إيموجي مناسب

قدم البايو المحسّن فقط بدون شرح."""

            elif content_type == "name":
                prompt = f"""حسّن هذا الاسم لحساب X ليكون أكثر جاذبية:

"{content}"

المتطلبات:
- احتفظ بالمعنى
- اجعله أسهل في النطق والتذكر
- يمكن تعديل الصياغة قليلاً

قدم الاسم المحسّن فقط بدون شرح."""

            else:
                return content
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "أنت خبير في تحسين المحتوى لحسابات التواصل الاجتماعي."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            refined = response.choices[0].message.content.strip()
            refined = refined.replace('"', '').replace("'", '').strip()
            
            return refined
            
        except Exception as e:
            print(f"[ERROR] GPT refinement failed: {e}")
            return content
    
    def generate_complete_profile(
        self,
        niche: Optional[str] = None,
        style: str = "professional",
        include_location: bool = True,
        include_website: bool = False
    ) -> Dict[str, Any]:
        """
        توليد هوية كاملة للحساب
        
        Args:
            niche: المجال أو التخصص
            style: نمط الهوية
            include_location: هل يتم إضافة موقع
            include_website: هل يتم إضافة موقع إلكتروني
            
        Returns:
            قاموس يحتوي على جميع عناصر الهوية
        """
        print(f"[INFO] Generating complete profile for niche: {niche}")
        
        # 1. توليد الاسم باستخدام Gemini
        print("[INFO] Generating name with Gemini...")
        name = self.generate_name_with_gemini(niche, style)
        
        # 2. تحسين الاسم باستخدام GPT
        print("[INFO] Refining name with GPT...")
        name = self.refine_with_gpt(name, "name")
        
        # 3. توليد البايو باستخدام Gemini
        print("[INFO] Generating bio with Gemini...")
        bio = self.generate_bio_with_gemini(name, niche, style)
        
        # 4. تحسين البايو باستخدام GPT
        print("[INFO] Refining bio with GPT...")
        bio = self.refine_with_gpt(bio, "bio")
        
        # 5. توليد موقع إذا طُلب
        location = None
        if include_location:
            location = self._generate_location(niche)
        
        # 6. توليد موقع إلكتروني إذا طُلب
        website = None
        if include_website:
            website = self._generate_website(name)
        
        profile = {
            "name": name,
            "bio": bio,
            "location": location,
            "website": website,
            "niche": niche,
            "style": style
        }
        
        print(f"[SUCCESS] Profile generated: {json.dumps(profile, ensure_ascii=False, indent=2)}")
        
        return profile
    
    def _generate_name_fallback(self, niche: Optional[str], style: str) -> str:
        """توليد اسم احتياطي إذا فشل Gemini"""
        if niche:
            return f"{niche} Expert"
        return "Content Creator"
    
    def _generate_bio_fallback(self, name: str, niche: Optional[str], tone: str) -> str:
        """توليد بايو احتياطي إذا فشل Gemini"""
        if niche:
            return f"🌟 {name} | متخصص في {niche} | مشاركة محتوى قيم يومياً"
        return f"✨ {name} | Content Creator | Sharing valuable insights"
    
    def _generate_location(self, niche: Optional[str]) -> str:
        """توليد موقع مناسب"""
        locations = [
            "الرياض، المملكة العربية السعودية",
            "دبي، الإمارات العربية المتحدة",
            "القاهرة، مصر",
            "عمّان، الأردن",
            "بيروت، لبنان"
        ]
        return locations[0]
    
    def _generate_website(self, name: str) -> str:
        """توليد رابط موقع إلكتروني"""
        clean_name = name.lower().replace(" ", "")
        return f"https://{clean_name}.com"
    
    def process_request(self, user_input: str) -> Dict[str, Any]:
        """
        معالجة طلب المستخدم
        
        Args:
            user_input: نص الطلب من المستخدم
            
        Returns:
            نتيجة المعالجة
        """
        # تحليل النية
        intent_data = self.detect_intent(user_input)
        intent = intent_data["intent"]
        
        if intent == "create_profile":
            # إنشاء هوية كاملة
            profile = self.generate_complete_profile(
                niche=intent_data.get("niche"),
                style="professional"
            )
            
            return {
                "success": True,
                "intent": "create_profile",
                "profile": profile,
                "account_name": intent_data.get("account_name"),
                "message": "✅ تم إنشاء الهوية بنجاح!"
            }
        
        elif intent == "generate_name":
            # توليد اسم فقط
            name = self.generate_name_with_gemini(intent_data.get("niche"))
            name = self.refine_with_gpt(name, "name")
            
            return {
                "success": True,
                "intent": "generate_name",
                "name": name,
                "message": f"✅ الاسم المقترح: {name}"
            }
        
        elif intent == "generate_bio":
            # توليد بايو فقط
            name = intent_data.get("account_name", "المستخدم")
            bio = self.generate_bio_with_gemini(name, intent_data.get("niche"))
            bio = self.refine_with_gpt(bio, "bio")
            
            return {
                "success": True,
                "intent": "generate_bio",
                "bio": bio,
                "message": f"✅ البايو المقترح: {bio}"
            }
        
        else:
            return {
                "success": False,
                "intent": "unknown",
                "message": "❌ لم أتمكن من فهم الطلب. يرجى توضيح ما تريد (إنشاء هوية، توليد اسم، توليد بايو)"
            }


# مثيل عام من الوكيل
profile_agent = ProfileAgent()


def generate_profile(niche: Optional[str] = None, style: str = "professional") -> Dict[str, Any]:
    """
    دالة مساعدة لتوليد هوية كاملة
    
    Args:
        niche: المجال أو التخصص
        style: نمط الهوية
        
    Returns:
        الهوية المولدة
    """
    return profile_agent.generate_complete_profile(niche=niche, style=style)


def process_profile_request(user_input: str) -> Dict[str, Any]:
    """
    دالة مساعدة لمعالجة طلب المستخدم
    
    Args:
        user_input: نص الطلب
        
    Returns:
        نتيجة المعالجة
    """
    return profile_agent.process_request(user_input)
