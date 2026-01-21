#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memory Service - خدمة إدارة ذاكرة المحادثات
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json

from app.db.database import get_db
from app.db.models import Conversation, Message, User


class MemoryService:
    """خدمة إدارة ذاكرة المحادثات والرسائل"""
    
    def __init__(self):
        pass
    
    def get_or_create_conversation(
        self,
        db: Session,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Conversation:
        """
        الحصول على محادثة موجودة أو إنشاء جديدة
        
        Args:
            db: جلسة قاعدة البيانات
            user_id: معرف المستخدم
            session_id: معرف الجلسة
            
        Returns:
            المحادثة
        """
        conversation = None
        
        # البحث عن محادثة موجودة
        if session_id:
            conversation = db.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()
        
        if not conversation and user_id:
            # البحث عن آخر محادثة للمستخدم
            conversation = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.updated_at.desc()).first()
            
            # إذا كانت المحادثة الأخيرة قديمة (أكثر من ساعة)، أنشئ جديدة
            if conversation:
                time_diff = datetime.utcnow() - conversation.updated_at
                if time_diff.total_seconds() > 3600:  # ساعة واحدة
                    conversation = None
        
        # إنشاء محادثة جديدة إذا لم توجد
        if not conversation:
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id,
                title="محادثة جديدة"
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        return conversation
    
    def add_message(
        self,
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        إضافة رسالة للمحادثة
        
        Args:
            db: جلسة قاعدة البيانات
            conversation_id: معرف المحادثة
            role: دور المرسل (user, assistant, system)
            content: محتوى الرسالة
            intent: النية المكتشفة
            confidence: مستوى الثقة
            agent: الوكيل الذي عالج الرسالة
            metadata: بيانات إضافية
            
        Returns:
            الرسالة المضافة
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            confidence=str(confidence) if confidence else None,
            agent=agent,
            extra_data=json.dumps(metadata) if metadata else None
        )
        
        db.add(message)
        
        # تحديث عنوان المحادثة من أول رسالة مستخدم
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation and role == "user" and conversation.title == "محادثة جديدة":
            # استخدم أول 50 حرف من الرسالة كعنوان
            conversation.title = content[:50] + ("..." if len(content) > 50 else "")
        
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return message
    
    def get_conversation_history(
        self,
        db: Session,
        conversation_id: int,
        limit: Optional[int] = 50
    ) -> List[Message]:
        """
        الحصول على تاريخ المحادثة
        
        Args:
            db: جلسة قاعدة البيانات
            conversation_id: معرف المحادثة
            limit: عدد الرسائل المطلوبة
            
        Returns:
            قائمة الرسائل
        """
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        return list(reversed(messages))
    
    def get_user_conversations(
        self,
        db: Session,
        user_id: int,
        limit: Optional[int] = 20
    ) -> List[Conversation]:
        """
        الحصول على محادثات المستخدم
        
        Args:
            db: جلسة قاعدة البيانات
            user_id: معرف المستخدم
            limit: عدد المحادثات
            
        Returns:
            قائمة المحادثات
        """
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).limit(limit).all()
        
        return conversations
    
    def get_conversation_context(
        self,
        db: Session,
        conversation_id: int,
        max_messages: int = 10
    ) -> str:
        """
        الحصول على سياق المحادثة للوكيل
        
        Args:
            db: جلسة قاعدة البيانات
            conversation_id: معرف المحادثة
            max_messages: عدد الرسائل الأخيرة
            
        Returns:
            نص السياق
        """
        messages = self.get_conversation_history(db, conversation_id, max_messages)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages:
            role_ar = "المستخدم" if msg.role == "user" else "المساعد"
            context_parts.append(f"{role_ar}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def get_user_preferences(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """
        استخراج تفضيلات المستخدم من المحادثات السابقة
        
        Args:
            db: جلسة قاعدة البيانات
            user_id: معرف المستخدم
            
        Returns:
            تفضيلات المستخدم
        """
        # الحصول على آخر 100 رسالة للمستخدم
        conversations = self.get_user_conversations(db, user_id, limit=10)
        
        preferences = {
            "total_conversations": len(conversations),
            "common_intents": [],
            "preferred_platforms": [],
            "last_interaction": None
        }
        
        if conversations:
            preferences["last_interaction"] = conversations[0].updated_at.isoformat()
            
            # تحليل النوايا الشائعة
            intent_counts = {}
            platform_counts = {}
            
            for conv in conversations:
                for msg in conv.messages:
                    if msg.intent:
                        intent_counts[msg.intent] = intent_counts.get(msg.intent, 0) + 1
                    
                    if msg.extra_data:
                        try:
                            extra_data = json.loads(msg.extra_data)
                            if extra_data.get("platform"):
                                platform = extra_data["platform"]
                                platform_counts[platform] = platform_counts.get(platform, 0) + 1
                        except:
                            pass
            
            # أكثر النوايا شيوعاً
            if intent_counts:
                sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)
                preferences["common_intents"] = [intent for intent, _ in sorted_intents[:5]]
            
            # المنصات المفضلة
            if platform_counts:
                sorted_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
                preferences["preferred_platforms"] = [platform for platform, _ in sorted_platforms[:3]]
        
        return preferences
    
    def delete_conversation(
        self,
        db: Session,
        conversation_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        حذف محادثة
        
        Args:
            db: جلسة قاعدة البيانات
            conversation_id: معرف المحادثة
            user_id: معرف المستخدم (للتحقق من الصلاحية)
            
        Returns:
            نجاح العملية
        """
        query = db.query(Conversation).filter(Conversation.id == conversation_id)
        
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        
        conversation = query.first()
        
        if conversation:
            db.delete(conversation)
            db.commit()
            return True
        
        return False


memory_service = MemoryService()
