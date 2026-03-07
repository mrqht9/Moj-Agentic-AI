from openai import AsyncOpenAI
from app.core.config import settings
import asyncio

class AIService:
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.conversation_history = []
    
    async def get_response(self, user_message: str) -> str:
        if not self.client:
            return "مرحباً! أنا مساعد AI. لتفعيل الذكاء الاصطناعي، يرجى إضافة OPENAI_API_KEY في ملف .env"
        
        try:
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "أنت مساعد ذكي متخصص في إدارة وسائل التواصل الاجتماعي والأتمتة. تتحدث العربية بطلاقة وتساعد المستخدمين في مهامهم."
                    },
                    *self.conversation_history
                ],
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE
            )
            
            assistant_message = response.choices[0].message.content
            
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            error_str = str(e)
            print(f"[AIService] Error: {error_str[:200]}")
            if "401" in error_str or "api_key" in error_str.lower() or "invalid_api_key" in error_str:
                return "عذراً، مفتاح الذكاء الاصطناعي يحتاج تحديث. تقدر تسألني عن الترندات مباشرة مثل: \"وش الترندات؟\" أو \"ترند السعودية\""
            return "عذراً، حدث خطأ مؤقت. جرب مرة ثانية أو اسألني عن الترندات مباشرة."
    
    def clear_history(self):
        self.conversation_history = []
