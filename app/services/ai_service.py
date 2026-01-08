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
            return f"عذراً، حدث خطأ في الاتصال بخدمة الذكاء الاصطناعي: {str(e)}"
    
    def clear_history(self):
        self.conversation_history = []
