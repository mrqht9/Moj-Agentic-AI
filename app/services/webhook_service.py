import httpx
from app.core.config import settings
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self):
        self.webhook_url = settings.N8N_WEBHOOK_URL
        self.enabled = settings.N8N_WEBHOOK_ENABLED and self.webhook_url is not None
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def send_message_to_n8n(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        إرسال رسالة المستخدم إلى n8n webhook
        
        Args:
            user_message: الرسالة التي أرسلها المستخدم
            session_id: معرف الجلسة (اختياري)
            user_id: معرف المستخدم (اختياري)
            metadata: بيانات إضافية (اختياري)
        
        Returns:
            bool: True إذا تم الإرسال بنجاح، False خلاف ذلك
        """
        if not self.enabled:
            logger.debug("N8N webhook is disabled")
            return False
        
        try:
            payload = {
                "message": user_message,
                "timestamp": datetime.now().isoformat(),
                "source": "moj_ai_chatbot",
                "type": "user_message"
            }
            
            # إضافة البيانات الاختيارية
            if session_id:
                payload["session_id"] = session_id
            
            if user_id:
                payload["user_id"] = user_id
            
            if metadata:
                payload["metadata"] = metadata
            
            # إرسال الطلب إلى n8n webhook
            response = await self.client.post(
                self.webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Moj-AI-Chatbot/2.0"
                }
            )
            
            response.raise_for_status()
            logger.info(f"Message sent to n8n webhook successfully. Status: {response.status_code}")
            return True
            
        except httpx.TimeoutException:
            logger.error("Timeout while sending message to n8n webhook")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while sending to n8n webhook: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error sending message to n8n webhook: {str(e)}")
            return False
    
    async def send_ai_response_to_n8n(
        self,
        user_message: str,
        ai_response: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        إرسال استجابة AI إلى n8n webhook (اختياري)
        
        Args:
            user_message: الرسالة الأصلية للمستخدم
            ai_response: استجابة AI
            session_id: معرف الجلسة (اختياري)
            user_id: معرف المستخدم (اختياري)
        
        Returns:
            bool: True إذا تم الإرسال بنجاح، False خلاف ذلك
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "user_message": user_message,
                "ai_response": ai_response,
                "timestamp": datetime.now().isoformat(),
                "source": "moj_ai_chatbot",
                "type": "ai_response"
            }
            
            if session_id:
                payload["session_id"] = session_id
            
            if user_id:
                payload["user_id"] = user_id
            
            response = await self.client.post(
                self.webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Moj-AI-Chatbot/2.0"
                }
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Error sending AI response to n8n webhook: {str(e)}")
            return False
    
    async def close(self):
        """إغلاق العميل HTTP"""
        await self.client.aclose()
