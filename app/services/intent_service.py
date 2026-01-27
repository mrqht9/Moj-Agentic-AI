#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Intent Recognition Service
نظام التعرف على نوايا المستخدم في إدارة حساباته على منصات التواصل الاجتماعي
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """أنواع النوايا المدعومة"""
    # إدارة الحسابات
    ADD_ACCOUNT = "add_account"
    REMOVE_ACCOUNT = "remove_account"
    LIST_ACCOUNTS = "list_accounts"
    SWITCH_ACCOUNT = "switch_account"
    
    # إدارة المحتوى
    CREATE_POST = "create_post"
    SCHEDULE_POST = "schedule_post"
    DELETE_POST = "delete_post"
    EDIT_POST = "edit_post"
    
    # التحليلات والإحصائيات
    GET_ANALYTICS = "get_analytics"
    GET_ENGAGEMENT = "get_engagement"
    GET_FOLLOWERS = "get_followers"
    
    # التفاعل
    REPLY_TO_COMMENT = "reply_to_comment"
    LIKE_POST = "like_post"
    SHARE_POST = "share_post"
    
    # الأتمتة
    CREATE_AUTOMATION = "create_automation"
    MANAGE_AUTOMATION = "manage_automation"
    
    # عام
    HELP = "help"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class Platform(str, Enum):
    """منصات التواصل الاجتماعي المدعومة"""
    TWITTER = "twitter"
    X = "x"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    ALL = "all"


class IntentResult:
    """نتيجة التعرف على النية"""
    def __init__(
        self,
        intent: IntentType,
        confidence: float,
        entities: Dict[str, Any],
        platform: Optional[Platform] = None,
        raw_text: str = ""
    ):
        self.intent = intent
        self.confidence = confidence
        self.entities = entities
        self.platform = platform
        self.raw_text = raw_text
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "entities": self.entities,
            "platform": self.platform.value if self.platform else None,
            "raw_text": self.raw_text,
            "timestamp": self.timestamp.isoformat()
        }


class IntentService:
    """خدمة التعرف على النوايا"""
    
    def __init__(self):
        self.intent_patterns = self._initialize_patterns()
        self.platform_keywords = self._initialize_platform_keywords()
    
    def _initialize_patterns(self) -> Dict[IntentType, List[str]]:
        """تهيئة أنماط التعرف على النوايا"""
        return {
            # إدارة الحسابات
            IntentType.ADD_ACCOUNT: [
                r"أضف حساب",
                r"إضافة حساب",
                r"ربط حساب",
                r"سجل حساب",
                r"أريد إضافة",
                r"تسجيل دخول",
                r"سجل دخول",
                r"تسجيل الدخول",
                r"ابي اسوي تسجيل",
                r"ابغى اسجل",
                r"ابي تسجل",
                r"ابيك تسجل",
                r"ابغاك تسجل",
                r"مرحبا ابي.*تسجل",
                r"ودي اسجل",
                r"ابغى اضيف حساب",
                r"ممكن اضيف",
                r"اضف لي حساب",
                r"سجل لي",
                r"دخلني",
                r"add account",
                r"connect account",
                r"link account",
                r"login",
                r"sign in",
                r"log in"
            ],
            IntentType.REMOVE_ACCOUNT: [
                r"احذف حساب",
                r"إزالة حساب",
                r"فك ربط",
                r"حذف حسابي",
                r"احذف حسابي",
                r"امسح حساب",
                r"ازالة حسابي",
                r"ابي احذف",
                r"ابغى احذف",
                r"ودي احذف",
                r"شيل حساب",
                r"الغي حساب",
                r"ابغى امسح",
                r"امسح لي",
                r"شيل لي",
                r"remove account",
                r"delete account",
                r"unlink account",
                r"remove my account",
                r"delete my account"
            ],
            IntentType.LIST_ACCOUNTS: [
                r"اعرض حساباتي",
                r"قائمة الحسابات",
                r"حساباتي",
                r"ما هي حساباتي",
                r"وش حساباتي",
                r"ايش عندي من حسابات",
                r"شوف حساباتي",
                r"ورني حساباتي",
                r"عندي كم حساب",
                r"كم حساب عندي",
                r"الحسابات المربوطة",
                r"الحسابات النشطة",
                r"list accounts",
                r"show accounts",
                r"my accounts",
                r"show my accounts",
                r"list my accounts"
            ],
            IntentType.SWITCH_ACCOUNT: [
                r"انتقل إلى حساب",
                r"غير الحساب",
                r"switch account",
                r"change account",
                r"استخدم حساب"
            ],
            
            # إدارة المحتوى
            IntentType.CREATE_POST: [
                r"انشر",
                r"اكتب منشور",
                r"أريد النشر",
                r"غرد",
                r"نشر",
                r"تغريد",
                r"تغريدة",
                r"نص التغريدة",
                r"طيب غرد",
                r"ابي انشر",
                r"ابغى اغرد",
                r"اكتب تغريدة",
                r"ودي انشر",
                r"ابغى اكتب",
                r"انشر لي",
                r"غرد لي",
                r"اكتب في",
                r"بوست",
                r"منشور",
                r"create post",
                r"publish post",
                r"write post",
                r"post",
                r"tweet",
                r"make a post",
                r"publish"
            ],
            IntentType.SCHEDULE_POST: [
                r"جدول منشور",
                r"انشر في وقت",
                r"schedule post",
                r"post later",
                r"انشر غداً",
                r"انشر بعد"
            ],
            IntentType.DELETE_POST: [
                r"احذف منشور",
                r"امسح منشور",
                r"delete post",
                r"remove post"
            ],
            IntentType.EDIT_POST: [
                r"عدل منشور",
                r"غير منشور",
                r"edit post",
                r"modify post",
                r"update post"
            ],
            
            # التحليلات
            IntentType.GET_ANALYTICS: [
                r"إحصائيات",
                r"تحليلات",
                r"analytics",
                r"statistics",
                r"stats",
                r"أداء",
                r"performance"
            ],
            IntentType.GET_ENGAGEMENT: [
                r"تفاعل",
                r"engagement",
                r"interactions",
                r"likes",
                r"إعجابات",
                r"تعليقات",
                r"comments"
            ],
            IntentType.GET_FOLLOWERS: [
                r"متابعين",
                r"followers",
                r"متابعون",
                r"عدد المتابعين"
            ],
            
            # التفاعل
            IntentType.REPLY_TO_COMMENT: [
                r"رد على",
                r"reply to",
                r"respond to",
                r"أجب على"
            ],
            IntentType.LIKE_POST: [
                r"أعجبني",
                r"like",
                r"إعجاب"
            ],
            IntentType.SHARE_POST: [
                r"شارك",
                r"share",
                r"retweet",
                r"أعد نشر"
            ],
            
            # الأتمتة
            IntentType.CREATE_AUTOMATION: [
                r"أتمت",
                r"automation",
                r"automate",
                r"جدول تلقائي",
                r"نشر تلقائي"
            ],
            
            # عام
            IntentType.HELP: [
                r"مساعدة",
                r"help",
                r"ساعدني",
                r"كيف",
                r"how to",
                r"ماذا يمكنك"
            ],
            IntentType.GREETING: [
                r"مرحبا",
                r"السلام عليكم",
                r"أهلا",
                r"هلا",
                r"اهلين",
                r"يا هلا",
                r"حياك",
                r"صباح الخير",
                r"مساء الخير",
                r"صباحك",
                r"مساك",
                r"كيف حالك",
                r"كيفك",
                r"شلونك",
                r"وش اخبارك",
                r"hello",
                r"hi",
                r"hey",
                r"good morning",
                r"good evening",
                r"how are you"
            ]
        }
    
    def _initialize_platform_keywords(self) -> Dict[Platform, List[str]]:
        """تهيئة كلمات مفتاحية للمنصات"""
        return {
            Platform.TWITTER: ["twitter", "تويتر", "tweet", "غرد", "x.com"],
            Platform.X: ["x", "إكس", "x.com"],
            Platform.INSTAGRAM: ["instagram", "انستقرام", "انستا", "insta"],
            Platform.FACEBOOK: ["facebook", "فيسبوك", "fb"],
            Platform.LINKEDIN: ["linkedin", "لينكد إن", "لينكدإن"],
            Platform.TIKTOK: ["tiktok", "تيك توك", "تيكتوك"]
        }
    
    def detect_intent(self, text: str) -> IntentResult:
        """
        التعرف على نية المستخدم من النص
        
        Args:
            text: النص المدخل من المستخدم
            
        Returns:
            IntentResult: نتيجة التعرف على النية
        """
        text_lower = text.lower()
        
        # البحث عن النية
        detected_intent = IntentType.UNKNOWN
        max_confidence = 0.0
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    confidence = self._calculate_confidence(text_lower, pattern)
                    if confidence > max_confidence:
                        max_confidence = confidence
                        detected_intent = intent_type
        
        # استخراج المنصة
        platform = self._detect_platform(text_lower)
        
        # استخراج الكيانات
        entities = self._extract_entities(text, detected_intent)
        
        logger.info(f"Intent detected: {detected_intent.value} (confidence: {max_confidence:.2f})")
        
        return IntentResult(
            intent=detected_intent,
            confidence=max_confidence,
            entities=entities,
            platform=platform,
            raw_text=text
        )
    
    def _calculate_confidence(self, text: str, pattern: str) -> float:
        """حساب مستوى الثقة في التعرف على النية"""
        # إذا كان النمط موجود بالضبط، ثقة عالية
        if re.search(f"\\b{pattern}\\b", text, re.IGNORECASE):
            return 0.95
        # إذا كان موجود كجزء من الكلمة
        elif re.search(pattern, text, re.IGNORECASE):
            return 0.75
        return 0.5
    
    def _detect_platform(self, text: str) -> Optional[Platform]:
        """التعرف على المنصة من النص"""
        for platform, keywords in self.platform_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return platform
        return None
    
    def _extract_entities(self, text: str, intent: IntentType) -> Dict[str, Any]:
        """استخراج الكيانات من النص حسب النية"""
        entities = {}
        
        # استخراج الوقت/التاريخ
        time_patterns = [
            (r"غداً|tomorrow", "tomorrow"),
            (r"بعد (\d+) ساعة|in (\d+) hour", "hours"),
            (r"في الساعة (\d+)", "time"),
            (r"(\d{1,2}):(\d{2})", "time")
        ]
        
        for pattern, entity_type in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities["schedule_time"] = {
                    "type": entity_type,
                    "value": match.group(0)
                }
        
        # استخراج اسم الحساب
        account_patterns = [
            r"من حساب\s+(\w+)",
            r"حساب\s+(\w+)",
            r"@(\w+)",
            r"account\s+(\w+)",
            r"في حساب\s+(\w+)",
            r"على حساب\s+(\w+)"
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities["account_name"] = match.group(1)
                break
        
        # استخراج محتوى المنشور
        if intent in [IntentType.CREATE_POST, IntentType.SCHEDULE_POST]:
            # البحث عن محتوى بين علامات اقتباس
            content_match = re.search(r'["\'](.+?)["\']|"(.+?)"|«(.+?)»', text)
            if content_match:
                entities["content"] = (
                    content_match.group(1) or 
                    content_match.group(2) or 
                    content_match.group(3)
                )
            else:
                # إذا لم يكن هناك علامات اقتباس، استخرج النص بعد الكلمات المفتاحية
                for keyword in ["غرد", "انشر", "تغريدة", "نص التغريدة", "tweet", "post"]:
                    if keyword in text.lower():
                        parts = text.lower().split(keyword, 1)
                        if len(parts) > 1:
                            content = parts[1].strip()
                            # إزالة كلمات مثل "في الحساب", "بالنص التالي", إلخ
                            content = re.sub(r'^(في الحساب|بالنص التالي|النص التالي|بالنص|:)\s*', '', content, flags=re.IGNORECASE)
                            if content:
                                entities["content"] = content
                                break
        
        # استخراج الأرقام
        numbers = re.findall(r'\d+', text)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]
        
        return entities
    
    def get_intent_suggestions(self, partial_text: str) -> List[Dict[str, str]]:
        """
        اقتراحات للنوايا بناءً على نص جزئي
        
        Args:
            partial_text: نص جزئي من المستخدم
            
        Returns:
            قائمة بالاقتراحات
        """
        suggestions = []
        text_lower = partial_text.lower()
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in text_lower or text_lower in pattern:
                    suggestions.append({
                        "intent": intent_type.value,
                        "example": pattern,
                        "description": self._get_intent_description(intent_type)
                    })
        
        return suggestions[:5]  # أول 5 اقتراحات
    
    def _get_intent_description(self, intent: IntentType) -> str:
        """وصف النية"""
        descriptions = {
            IntentType.ADD_ACCOUNT: "إضافة حساب جديد على منصة التواصل",
            IntentType.CREATE_POST: "إنشاء ونشر منشور جديد",
            IntentType.SCHEDULE_POST: "جدولة منشور للنشر في وقت لاحق",
            IntentType.GET_ANALYTICS: "عرض إحصائيات وتحليلات الحساب",
            IntentType.LIST_ACCOUNTS: "عرض قائمة الحسابات المرتبطة",
            IntentType.HELP: "الحصول على مساعدة",
        }
        return descriptions.get(intent, "")


# مثيل واحد من الخدمة
intent_service = IntentService()
