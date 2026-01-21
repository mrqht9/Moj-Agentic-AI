#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Conversation API Routes
API endpoints لإدارة المحادثات والذاكرة
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.memory_service import memory_service
from app.db.database import get_db
from app.db.models import Conversation, Message
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


class ConversationResponse(BaseModel):
    """استجابة محادثة"""
    id: int
    user_id: Optional[int]
    session_id: Optional[str]
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    """استجابة رسالة"""
    id: int
    role: str
    content: str
    intent: Optional[str]
    confidence: Optional[str]
    agent: Optional[str]
    created_at: str


class ConversationDetailResponse(BaseModel):
    """استجابة تفاصيل محادثة"""
    conversation: ConversationResponse
    messages: List[MessageResponse]


class UserPreferencesResponse(BaseModel):
    """استجابة تفضيلات المستخدم"""
    total_conversations: int
    common_intents: List[str]
    preferred_platforms: List[str]
    last_interaction: Optional[str]


@router.get("/", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_id: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    الحصول على محادثات المستخدم
    
    Args:
        user_id: معرف المستخدم (اختياري)
        limit: عدد المحادثات
        db: جلسة قاعدة البيانات
        current_user: المستخدم الحالي
    
    Returns:
        قائمة المحادثات
    """
    try:
        # استخدام user_id من current_user إذا كان متاحاً
        if current_user:
            user_id = current_user.id
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id مطلوب")
        
        conversations = memory_service.get_user_conversations(db, user_id, limit)
        
        return [
            ConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                session_id=conv.session_id,
                title=conv.title or "محادثة",
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                message_count=len(conv.messages)
            )
            for conv in conversations
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في الحصول على المحادثات: {str(e)}"
        )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    الحصول على تفاصيل محادثة محددة
    
    Args:
        conversation_id: معرف المحادثة
        db: جلسة قاعدة البيانات
        current_user: المستخدم الحالي
    
    Returns:
        تفاصيل المحادثة مع الرسائل
    """
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="المحادثة غير موجودة")
        
        # التحقق من الصلاحية
        if current_user and conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="غير مصرح لك بالوصول لهذه المحادثة")
        
        messages = memory_service.get_conversation_history(db, conversation_id)
        
        return ConversationDetailResponse(
            conversation=ConversationResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                session_id=conversation.session_id,
                title=conversation.title or "محادثة",
                created_at=conversation.created_at.isoformat(),
                updated_at=conversation.updated_at.isoformat(),
                message_count=len(messages)
            ),
            messages=[
                MessageResponse(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    intent=msg.intent,
                    confidence=msg.confidence,
                    agent=msg.agent,
                    created_at=msg.created_at.isoformat()
                )
                for msg in messages
            ]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في الحصول على المحادثة: {str(e)}"
        )


@router.get("/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: int,
    max_messages: int = 10,
    db: Session = Depends(get_db)
):
    """
    الحصول على سياق المحادثة
    
    Args:
        conversation_id: معرف المحادثة
        max_messages: عدد الرسائل الأخيرة
        db: جلسة قاعدة البيانات
    
    Returns:
        سياق المحادثة
    """
    try:
        context = memory_service.get_conversation_context(
            db, conversation_id, max_messages
        )
        
        return {
            "conversation_id": conversation_id,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في الحصول على السياق: {str(e)}"
        )


@router.get("/user/{user_id}/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    الحصول على تفضيلات المستخدم من المحادثات السابقة
    
    Args:
        user_id: معرف المستخدم
        db: جلسة قاعدة البيانات
        current_user: المستخدم الحالي
    
    Returns:
        تفضيلات المستخدم
    """
    try:
        # التحقق من الصلاحية
        if current_user and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="غير مصرح لك بالوصول لهذه البيانات")
        
        preferences = memory_service.get_user_preferences(db, user_id)
        
        return UserPreferencesResponse(**preferences)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في الحصول على التفضيلات: {str(e)}"
        )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    حذف محادثة
    
    Args:
        conversation_id: معرف المحادثة
        db: جلسة قاعدة البيانات
        current_user: المستخدم الحالي
    
    Returns:
        نتيجة الحذف
    """
    try:
        user_id = current_user.id if current_user else None
        
        success = memory_service.delete_conversation(db, conversation_id, user_id)
        
        if success:
            return {
                "status": "success",
                "message": "تم حذف المحادثة بنجاح",
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="المحادثة غير موجودة أو لا يمكن حذفها")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في حذف المحادثة: {str(e)}"
        )


@router.get("/stats/summary")
async def get_conversations_summary(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    الحصول على ملخص إحصائيات المحادثات
    
    Args:
        user_id: معرف المستخدم
        db: جلسة قاعدة البيانات
        current_user: المستخدم الحالي
    
    Returns:
        ملخص الإحصائيات
    """
    try:
        if current_user:
            user_id = current_user.id
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id مطلوب")
        
        conversations = memory_service.get_user_conversations(db, user_id, limit=100)
        
        total_messages = sum(len(conv.messages) for conv in conversations)
        
        # حساب النوايا الأكثر استخداماً
        intent_counts = {}
        for conv in conversations:
            for msg in conv.messages:
                if msg.intent:
                    intent_counts[msg.intent] = intent_counts.get(msg.intent, 0) + 1
        
        top_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_conversations": len(conversations),
            "total_messages": total_messages,
            "top_intents": [{"intent": intent, "count": count} for intent, count in top_intents],
            "last_conversation": conversations[0].updated_at.isoformat() if conversations else None,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في الحصول على الإحصائيات: {str(e)}"
        )
