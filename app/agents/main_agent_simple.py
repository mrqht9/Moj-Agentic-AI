#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
الوكيل الرئيسي - نسخة مبسطة بدون autogen
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from .tools import detect_user_intent
from .x_agent_simple import XAgent
from .trend_agent import TrendAgent
from app.services.memory_service import memory_service


class MainAgent:
    """الوكيل الرئيسي المبسط"""
    
    TREND_INTENTS = {"get_trends", "get_hot_trends", "search_trends", "run_trends", "trend_detail"}
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.x_agent = XAgent(llm_config)
        self.trend_agent = TrendAgent(llm_config)
    
    def process_message(
        self, 
        message: str, 
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        db: Optional[Session] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """معالجة رسالة من المستخدم"""
        
        conversation_id = None
        
        # إنشاء أو الحصول على المحادثة
        if db:
            try:
                conversation = memory_service.get_or_create_conversation(
                    db=db, user_id=user_id, session_id=session_id
                )
                conversation_id = conversation.id
                
                # إضافة رسالة المستخدم
                memory_service.add_message(
                    db=db,
                    conversation_id=conversation_id,
                    role="user",
                    content=message
                )
            except Exception as e:
                print(f"Warning: Memory service error: {str(e)}")
        
        try:
            # تحليل النية
            intent_result = detect_user_intent(message)
            intent = intent_result.get("intent")
            platform = intent_result.get("platform")
            entities = intent_result.get("entities", {})
            confidence = intent_result.get("confidence", 0)
            
            if confidence < 0.5:
                # لا ترجع رد تلقائي - دع الوكيل يتعامل مع الطلب
                return None
            
            # توجيه للوكيل المناسب
            if intent in self.TREND_INTENTS:
                trend_context = {
                    "intent": intent,
                    "entities": entities,
                    "raw_text": message,
                }
                trend_response = self.trend_agent.process_request(message, trend_context, db)
                
                if trend_response:
                    if db and conversation_id:
                        try:
                            memory_service.add_message(
                                db=db, conversation_id=conversation_id,
                                role="assistant", content=trend_response,
                                intent=intent, confidence=confidence, agent="Trend_Agent"
                            )
                        except: pass
                    
                    return {
                        "success": True,
                        "message": trend_response,
                        "intent_result": intent_result,
                        "agent": "Trend_Agent",
                        "conversation_id": conversation_id
                    }
            
            elif platform in ["twitter", "x"] or intent in ["add_account", "create_post", "schedule_post"]:
                context = {
                    "intent": intent,
                    "entities": entities,
                    "platform": platform,
                    "user_id": user_id
                }
                
                x_response = self.x_agent.process_request(message, context)
                
                # إذا لم يرجع X_Agent رد
                if not x_response:
                    print(f"[DEBUG] X_Agent returned no response for intent: {intent}")
                    return {
                        "success": False,
                        "message": None,  # لا رد تلقائي
                        "intent_result": intent_result
                    }
                
                # حفظ الرد
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
                        print(f"Warning: Failed to save message: {str(e)}")
                
                return {
                    "success": True,
                    "message": x_response,
                    "intent_result": intent_result,
                    "agent": "X_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "help":
                help_message = """مرحباً! يمكنني مساعدتك في:

📱 **إدارة الحسابات:**
- إضافة حساب جديد على X
- عرض قائمة الحسابات

📝 **إدارة المحتوى:**
- نشر تغريدات
- جدولة منشورات

📊 **تحليل الترندات:**
- "وش الترندات؟" — نظرة عامة على الترندات
- "ترندات حارة" — عرض الترندات HOT فقط
- "ابحث ترند [كلمة]" — بحث في الترندات
- "حالة الترندات" — حالة النظام

أمثلة:
- "أضف حساب تويتر"
- "وش يتصدر اليوم؟"
- "ابحث ترند الذكاء الاصطناعي"

كيف يمكنني مساعدتك؟"""
                
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=help_message,
                            intent=intent, confidence=confidence, agent="Main_Agent"
                        )
                    except: pass
                
                return {
                    "success": True,
                    "message": help_message,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "greeting":
                greeting_msg = "مرحباً! 👋 أنا هنا لمساعدتك في إدارة حساباتك على منصات التواصل الاجتماعي. كيف يمكنني مساعدتك اليوم؟"
                
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=greeting_msg,
                            intent=intent, confidence=confidence, agent="Main_Agent"
                        )
                    except: pass
                
                return {
                    "success": True,
                    "message": greeting_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            elif intent == "list_accounts":
                # عرض حسابات المستخدم النشطة من قاعدة البيانات
                accounts_msg = ""
                
                if db and user_id:
                    try:
                        from app.services.account_service import account_service
                        
                        # الحصول على الحسابات النشطة فقط
                        accounts = account_service.get_user_accounts(
                            db=db,
                            user_id=user_id,
                            status="active"
                        )
                        
                        if accounts:
                            accounts_msg = f"📋 **حساباتك النشطة:**\n\n"
                            
                            # تجميع الحسابات حسب المنصة
                            platforms = {}
                            for account in accounts:
                                platform_name = account.platform
                                if platform_name == "x":
                                    platform_name = "X (Twitter)"
                                elif platform_name == "instagram":
                                    platform_name = "Instagram"
                                elif platform_name == "facebook":
                                    platform_name = "Facebook"
                                elif platform_name == "linkedin":
                                    platform_name = "LinkedIn"
                                elif platform_name == "tiktok":
                                    platform_name = "TikTok"
                                
                                if platform_name not in platforms:
                                    platforms[platform_name] = []
                                platforms[platform_name].append(account)
                            
                            # عرض الحسابات مجمعة حسب المنصة
                            for platform_name, platform_accounts in platforms.items():
                                accounts_msg += f"\n🌐 **{platform_name}:**\n"
                                for account in platform_accounts:
                                    accounts_msg += f"  • 👤 {account.username}"
                                    if account.last_used:
                                        from datetime import datetime
                                        last_used = account.last_used.strftime("%Y-%m-%d")
                                        accounts_msg += f" (آخر استخدام: {last_used})"
                                    accounts_msg += "\n"
                            
                            accounts_msg += f"\n✅ لديك {len(accounts)} حساب نشط"
                        else:
                            accounts_msg = "⚠️ لا توجد حسابات نشطة حالياً.\n\nيمكنك إضافة حساب بقول: سجل دخول اليوزر [username] الباسورد [password]"
                    
                    except Exception as e:
                        print(f"Error fetching accounts: {e}")
                        accounts_msg = "⚠️ حدث خطأ في جلب الحسابات. يرجى المحاولة مرة أخرى."
                else:
                    accounts_msg = "⚠️ لا توجد حسابات محفوظة حالياً.\n\nيمكنك إضافة حساب بقول: سجل دخول اليوزر [username] الباسورد [password]"
                
                if db and conversation_id:
                    try:
                        memory_service.add_message(
                            db=db, conversation_id=conversation_id,
                            role="assistant", content=accounts_msg,
                            intent=intent, confidence=confidence, agent="Main_Agent"
                        )
                    except: pass
                
                return {
                    "success": True,
                    "message": accounts_msg,
                    "intent_result": intent_result,
                    "agent": "Main_Agent",
                    "conversation_id": conversation_id
                }
            
            else:
                # ميزة غير متاحة
                print(f"[DEBUG] Feature not available: {intent}")
                return {
                    "success": False,
                    "message": None,  # لا رد تلقائي
                    "intent_result": intent_result
                }
        
        except Exception as e:
            # في حالة الخطأ، سجل الخطأ
            print(f"[ERROR] Main Agent error: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": None,  # لا رد تلقائي
                "error": str(e)
            }
