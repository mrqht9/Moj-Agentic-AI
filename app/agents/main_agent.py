#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
الوكيل الرئيسي
Main Orchestrator Agent
"""

from typing import Dict, Any, Optional
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from sqlalchemy.orm import Session
from .tools import detect_user_intent
from .x_agent import XAgent
from app.services.memory_service import memory_service
from app.db.database import get_db


class MainAgent:
    """الوكيل الرئيسي الذي ينسق بين الوكلاء الفرعيين"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        تهيئة الوكيل الرئيسي
        
        Args:
            llm_config: إعدادات نموذج اللغة
        """
        self.llm_config = llm_config
        
        # استخدام AssistantAgent بدلاً من ConversableAgent
        self.agent = AssistantAgent(
            name="MainAgent",
            model_client=llm_config,
            system_message="""أنت وكيل ذكي رئيسي متخصص في إدارة منصات التواصل الاجتماعي.
            
مهامك:
1. تحليل نوايا المستخدم من الرسائل
2. توجيه الطلبات للوكلاء الفرعيين المناسبين
3. التعامل مع الاستفسارات العامة
4. تقديم المساعدة والتوجيه

يمكنك استخدام الأدوات المتاحة لتحليل النوايا وتنفيذ المهام.""",
3. حدد الوكيل المناسب حسب النية والمنصة
4. أرسل الطلب للوكيل الفرعي
5. أرجع النتيجة للمستخدم

النوايا المدعومة:
- add_account: إضافة حساب جديد
- create_post: نشر منشور
- schedule_post: جدولة منشور
- get_analytics: عرض الإحصائيات
- list_accounts: عرض الحسابات
- help: المساعدة

المنصات المدعومة:
- X (Twitter)
- Instagram (قريباً)
- Facebook (قريباً)

تحدث بالعربية وكن مفيداً ومنظماً.""",
            llm_config=llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
        )
        
        self.x_agent = XAgent(llm_config)
        
        self._register_tools()
    
    def _register_tools(self):
        """تسجيل الأدوات المتاحة للوكيل الرئيسي"""
        # في الإصدار الجديد، الأدوات تُستخدم مباشرة بدون تسجيل
        pass
    
    def process_message(
        self, 
        message: str, 
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        معالجة رسالة من المستخدم مع حفظ في الذاكرة
        
        Args:
            message: رسالة المستخدم
            user_id: معرف المستخدم
            session_id: معرف الجلسة
            db: جلسة قاعدة البيانات
            
        Returns:
            الرد والمعلومات الإضافية
        """
        conversation_id = None
        
        # إنشاء أو الحصول على المحادثة
        if db:
            try:
                conversation = memory_service.get_or_create_conversation(
                    db=db,
                    user_id=user_id,
                    session_id=session_id
                )
                conversation_id = conversation.id
                
                # الحصول على سياق المحادثة السابقة
                context = memory_service.get_conversation_context(db, conversation_id, max_messages=10)
                
                # الحصول على تفضيلات المستخدم
                preferences = {}
                if user_id:
                    preferences = memory_service.get_user_preferences(db, user_id)
                
                # إضافة رسالة المستخدم
                memory_service.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message
                )
            except Exception as e:
                print(f"Warning: Memory service error: {str(e)}")
                context = ""
                preferences = {}
        else:
            context = ""
            preferences = {}
        
        try:
            intent_result = detect_user_intent(message)
            
            intent = intent_result.get("intent")
            platform = intent_result.get("platform")
            entities = intent_result.get("entities", {})
            confidence = intent_result.get("confidence", 0)
            
            # إضافة السياق والتفضيلات للرسالة إذا كانت متاحة
            enhanced_message = message
            if context:
                enhanced_message = f"السياق السابق:\n{context}\n\nالرسالة الحالية: {message}"
            
            if preferences.get("preferred_platforms"):
                enhanced_message += f"\n\nملاحظة: المستخدم يفضل استخدام: {', '.join(preferences['preferred_platforms'])}"
            
            if confidence < 0.5:
                return {
                    "success": False,
                    "message": "عذراً، لم أتمكن من فهم طلبك. هل يمكنك إعادة صياغته؟",
                    "intent_result": intent_result
                }
            
            if platform in ["twitter", "x"] or intent in ["add_account", "create_post", "schedule_post"]:
                agent_context = {
                    "intent": intent,
                    "entities": entities,
                    "platform": platform,
                    "user_id": user_id
                }
                
                x_response = self.x_agent.process_request(enhanced_message, agent_context)
                
                # حفظ رد المساعد في الذاكرة
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=x_response,
                            intent=intent,
                            confidence=confidence,
                            agent="X_Agent",
                            metadata={"platform": platform, "entities": entities}
                        )
                    except Exception as e:
                        print(f"Warning: Failed to save assistant message: {str(e)}")
                
                return {
                    "success": True,
                    "message": x_response,
                    "intent_result": intent_result,
                    "agent": "X_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "help":
                help_message = """مرحباً! يمكنني مساعدتك في:

📱 إدارة الحسابات:
- إضافة حساب جديد على X
- عرض قائمة الحسابات

📝 إدارة المحتوى:
- نشر تغريدات
- جدولة منشورات
- تحديث الملف الشخصي

📊 التحليلات:
- عرض الإحصائيات
- معدلات التفاعل

أمثلة:
- "أضف حساب تويتر"
- "انشر تغريدة 'مرحباً بالجميع!'"
- "حدث صورة الملف الشخصي"

كيف يمكنني مساعدتك؟"""
                
                # حفظ في الذاكرة
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=help_message,
                            intent=intent,
                            confidence=confidence,
                            agent="Main_Agent"
                        )
                    except Exception as e:
                        print(f"Warning: Failed to save message: {str(e)}")
                
                return {
                    "success": True,
                    "message": help_message,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "greeting":
                greeting_msg = "مرحباً! 👋 أنا هنا لمساعدتك في إدارة حساباتك على منصات التواصل الاجتماعي. كيف يمكنني مساعدتك اليوم؟"
                
                # حفظ في الذاكرة
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=greeting_msg,
                            intent=intent,
                            confidence=confidence,
                            agent="Main_Agent"
                        )
                    except Exception as e:
                        print(f"Warning: Failed to save message: {str(e)}")
                
                return {
                    "success": True,
                    "message": greeting_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "list_accounts":
                list_msg = "سأعرض لك قائمة الحسابات المرتبطة..."
                
                # حفظ في الذاكرة
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=list_msg,
                            intent=intent,
                            confidence=confidence,
                            agent="Main_Agent"
                        )
                    except Exception as e:
                        print(f"Warning: Failed to save message: {str(e)}")
                
                return {
                    "success": True,
                    "message": list_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "action": "list_accounts",
                    "conversation_id": conversation_id
                }
            
            else:
                error_msg = f"عذراً، هذه الميزة ({intent}) غير متاحة حالياً. جرب:\n- إضافة حساب\n- نشر تغريدة\n- تحديث الملف الشخصي"
                
                # حفظ في الذاكرة
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation_id,
                            role="assistant",
                            content=error_msg,
                            intent=intent,
                            confidence=confidence,
                            agent="Main_Agent"
                        )
                    except Exception as e:
                        print(f"Warning: Failed to save message: {str(e)}")
                
                return {
                    "success": False,
                    "message": error_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"حدث خطأ أثناء معالجة الطلب: {str(e)}",
                "error": str(e)
            }
    
    def get_agent(self) -> ConversableAgent:
        """الحصول على كائن الوكيل الرئيسي"""
        return self.agent
    
    def get_x_agent(self) -> XAgent:
        """الحصول على وكيل X"""
        return self.x_agent
