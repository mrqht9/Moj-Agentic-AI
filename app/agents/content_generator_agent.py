#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content Generator Agent - وكيل توليد المحتوى
مسؤول عن إنشاء محتوى تغريدات ذكي باستخدام OpenAI
"""

from typing import Dict, Any, Optional, List
import openai
from app.core.config import settings


class ContentGeneratorAgent:
    """وكيل توليد المحتوى الذكي"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL or "gpt-4"
        self.max_tokens = settings.OPENAI_MAX_TOKENS or 500
        self.temperature = settings.OPENAI_TEMPERATURE or 0.7
        
        if self.api_key:
            openai.api_key = self.api_key
    
    def generate_tweet(
        self,
        topic: str,
        style: Optional[str] = None,
        language: str = "arabic",
        max_length: int = 280,
        tone: Optional[str] = None,
        include_hashtags: bool = False,
        include_emoji: bool = True
    ) -> Dict[str, Any]:
        """
        توليد تغريدة بناءً على موضوع معين
        
        Args:
            topic: موضوع التغريدة
            style: نمط الكتابة (ملهم، فكاهي، احترافي، إلخ)
            language: اللغة (arabic, english)
            max_length: الحد الأقصى لطول التغريدة
            tone: نبرة الصوت (رسمي، ودي، حماسي، إلخ)
            include_hashtags: إضافة هاشتاقات
            include_emoji: إضافة إيموجي
            
        Returns:
            نتيجة التوليد مع المحتوى
        """
        if not self.api_key:
            return {
                "success": False,
                "message": "⚠️ مفتاح OpenAI API غير متوفر. يرجى إضافته في ملف .env",
                "content": None
            }
        
        try:
            # بناء الـ prompt
            prompt = self._build_prompt(
                topic=topic,
                style=style,
                language=language,
                max_length=max_length,
                tone=tone,
                include_hashtags=include_hashtags,
                include_emoji=include_emoji
            )
            
            # استدعاء OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(language)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                n=1
            )
            
            # استخراج المحتوى
            content = response.choices[0].message.content.strip()
            
            # تنظيف المحتوى
            content = self._clean_content(content, max_length)
            
            return {
                "success": True,
                "message": "تم توليد المحتوى بنجاح",
                "content": content,
                "metadata": {
                    "topic": topic,
                    "style": style,
                    "language": language,
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens
                }
            }
        
        except openai.error.AuthenticationError:
            return {
                "success": False,
                "message": "❌ خطأ في مفتاح OpenAI API. تحقق من صحة المفتاح.",
                "content": None
            }
        
        except openai.error.RateLimitError:
            return {
                "success": False,
                "message": "⚠️ تم تجاوز حد الاستخدام. حاول مرة أخرى لاحقاً.",
                "content": None
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ خطأ في توليد المحتوى: {str(e)}",
                "content": None
            }
    
    def generate_multiple_tweets(
        self,
        topic: str,
        count: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        توليد عدة تغريدات حول نفس الموضوع
        
        Args:
            topic: موضوع التغريدات
            count: عدد التغريدات المطلوبة
            **kwargs: معاملات إضافية للتوليد
            
        Returns:
            قائمة بالتغريدات المولدة
        """
        if not self.api_key:
            return {
                "success": False,
                "message": "⚠️ مفتاح OpenAI API غير متوفر",
                "tweets": []
            }
        
        tweets = []
        for i in range(count):
            result = self.generate_tweet(topic=topic, **kwargs)
            if result["success"]:
                tweets.append(result["content"])
        
        if tweets:
            return {
                "success": True,
                "message": f"تم توليد {len(tweets)} تغريدة بنجاح",
                "tweets": tweets,
                "count": len(tweets)
            }
        else:
            return {
                "success": False,
                "message": "فشل توليد التغريدات",
                "tweets": []
            }
    
    def _build_prompt(
        self,
        topic: str,
        style: Optional[str],
        language: str,
        max_length: int,
        tone: Optional[str],
        include_hashtags: bool,
        include_emoji: bool
    ) -> str:
        """بناء الـ prompt لـ OpenAI"""
        
        lang_name = "العربية" if language == "arabic" else "English"
        
        prompt = f"اكتب تغريدة عن: {topic}\n\n"
        prompt += f"المتطلبات:\n"
        prompt += f"- اللغة: {lang_name}\n"
        prompt += f"- الحد الأقصى: {max_length} حرف\n"
        
        if style:
            prompt += f"- الأسلوب: {style}\n"
        
        if tone:
            prompt += f"- النبرة: {tone}\n"
        
        if include_emoji:
            prompt += f"- أضف إيموجي مناسب\n"
        
        if include_hashtags:
            prompt += f"- أضف 1-3 هاشتاقات ذات صلة\n"
        
        prompt += f"\nاكتب التغريدة مباشرة بدون مقدمات أو شروحات."
        
        return prompt
    
    def _get_system_prompt(self, language: str) -> str:
        """الحصول على system prompt"""
        if language == "arabic":
            return """أنت كاتب محتوى محترف متخصص في كتابة تغريدات جذابة ومؤثرة باللغة العربية.
مهمتك هي كتابة تغريدات قصيرة، واضحة، وجذابة تناسب منصة X (تويتر).
اكتب بأسلوب طبيعي وجذاب، واستخدم الإيموجي بشكل مناسب.
تجنب الإطالة والتعقيد. اجعل التغريدة مباشرة ومؤثرة."""
        else:
            return """You are a professional content writer specialized in creating engaging and impactful tweets.
Your task is to write short, clear, and attractive tweets suitable for X (Twitter).
Write in a natural and engaging style, and use emojis appropriately.
Avoid being too long or complex. Make the tweet direct and impactful."""
    
    def _clean_content(self, content: str, max_length: int) -> str:
        """تنظيف المحتوى المولد"""
        # إزالة علامات الاقتباس الزائدة
        content = content.strip('"\'""''')
        
        # إزالة أي نصوص توضيحية
        if content.startswith("التغريدة:") or content.startswith("Tweet:"):
            content = content.split(":", 1)[1].strip()
        
        # التأكد من الطول
        if len(content) > max_length:
            content = content[:max_length-3] + "..."
        
        return content.strip()
    
    def suggest_topics(self, category: str) -> List[str]:
        """اقتراح مواضيع للتغريدات"""
        topics_db = {
            "تحفيزي": [
                "النجاح والإنجاز",
                "التغلب على الصعوبات",
                "الأحلام والطموحات",
                "قوة الإرادة",
                "التطوير الذاتي"
            ],
            "ديني": [
                "الشكر والحمد",
                "الصبر والرضا",
                "الدعاء والتضرع",
                "التفاؤل والأمل",
                "الأخلاق الحسنة"
            ],
            "تقني": [
                "الذكاء الاصطناعي",
                "البرمجة والتطوير",
                "التكنولوجيا الحديثة",
                "الأمن السيبراني",
                "مستقبل التقنية"
            ],
            "اجتماعي": [
                "العلاقات الإنسانية",
                "التواصل الفعال",
                "الصداقة والأخوة",
                "العائلة والأسرة",
                "المجتمع والتعاون"
            ],
            "ثقافي": [
                "القراءة والمعرفة",
                "الفن والإبداع",
                "التاريخ والحضارة",
                "اللغة والأدب",
                "الثقافة والتراث"
            ]
        }
        
        return topics_db.get(category, [])
    
    def analyze_tweet_quality(self, content: str) -> Dict[str, Any]:
        """تحليل جودة التغريدة"""
        analysis = {
            "length": len(content),
            "has_emoji": any(char for char in content if ord(char) > 127000),
            "has_hashtag": "#" in content,
            "word_count": len(content.split()),
            "quality_score": 0
        }
        
        # حساب نقاط الجودة
        score = 0
        
        # الطول المثالي (100-250 حرف)
        if 100 <= analysis["length"] <= 250:
            score += 30
        elif analysis["length"] <= 280:
            score += 20
        
        # وجود إيموجي
        if analysis["has_emoji"]:
            score += 20
        
        # وجود هاشتاق
        if analysis["has_hashtag"]:
            score += 15
        
        # عدد الكلمات المناسب
        if 10 <= analysis["word_count"] <= 40:
            score += 35
        
        analysis["quality_score"] = score
        analysis["quality_level"] = (
            "ممتاز" if score >= 80 else
            "جيد جداً" if score >= 60 else
            "جيد" if score >= 40 else
            "مقبول"
        )
        
        return analysis
