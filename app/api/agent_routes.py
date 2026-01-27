#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent API Routes
API endpoints لنظام الوكلاء الذكية
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.agents.agent_manager import agent_manager
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/agent", tags=["AI Agents"])


class AgentMessageRequest(BaseModel):
    """طلب رسالة للوكيل"""
    message: str = Field(..., description="رسالة المستخدم")
    user_id: Optional[int] = Field(None, description="معرف المستخدم")
    context: Optional[Dict[str, Any]] = Field(None, description="سياق إضافي")


class AgentMessageResponse(BaseModel):
    """استجابة الوكيل"""
    success: bool = Field(..., description="نجاح العملية")
    message: str = Field(..., description="رد الوكيل")
    intent_result: Optional[Dict[str, Any]] = Field(None, description="نتيجة تحليل النية")
    agent: Optional[str] = Field(None, description="الوكيل الذي عالج الطلب")
    action: Optional[str] = Field(None, description="الإجراء المطلوب")
    timestamp: str = Field(..., description="وقت المعالجة")


@router.post("/message", response_model=AgentMessageResponse)
async def send_message_to_agent(
    request: AgentMessageRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    إرسال رسالة إلى نظام الوكلاء الذكية
    
    يقوم هذا الـ endpoint بـ:
    1. استقبال رسالة المستخدم
    2. تحليل النية باستخدام Intent System
    3. توجيه الطلب للوكيل المناسب (X Agent, Instagram Agent, إلخ)
    4. تنفيذ الإجراء المطلوب
    5. إرجاع النتيجة
    
    أمثلة:
    - "أضف حساب تويتر"
    - "انشر تغريدة 'مرحباً بالجميع!'"
    - "حدث صورة الملف الشخصي"
    """
    try:
        agent_manager.initialize()
        
        user_id = request.user_id
        if current_user:
            user_id = current_user.id
        
        # معالجة الرسالة
        result = agent_manager.process_user_message(
            message=request.message,
            user_id=user_id
        )
        
        # إذا كان result None (لم يتعرف على النية أو ثقة منخفضة)
        if result is None or not isinstance(result, dict):
            return {
                "success": True,
                "message": "أنا هنا لمساعدتك! 😊 يمكنني مساعدتك في إدارة حساباتك على X (Twitter) والنشر والمزيد. قل 'مساعدة' لعرض الأوامر المتاحة.",
                "timestamp": datetime.now().isoformat()
            }
        
        # إذا كان message في result هو None
        if result.get("message") is None:
            return {
                "success": True,
                "message": "شكراً لك! 👍 كيف يمكنني مساعدتك اليوم؟ قل 'مساعدة' لعرض ما يمكنني فعله.",
                "intent": result.get("intent_result", {}).get("intent") if result.get("intent_result") else None,
                "confidence": result.get("intent_result", {}).get("confidence") if result.get("intent_result") else None,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", "تمت معالجة الطلب"),
            "intent": result.get("intent_result", {}).get("intent") if result.get("intent_result") else None,
            "confidence": result.get("intent_result", {}).get("confidence") if result.get("intent_result") else None,
            "agent": result.get("agent"),
            "conversation_id": result.get("conversation_id"),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في معالجة الرسالة: {str(e)}"
        )


@router.get("/health")
async def agent_health_check():
    """
    فحص صحة نظام الوكلاء
    """
    try:
        agent_manager.initialize()
        main_agent = agent_manager.get_main_agent()
        
        return {
            "status": "healthy",
            "main_agent": "initialized" if main_agent else "not_initialized",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/reset")
async def reset_agents(
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    إعادة تعيين نظام الوكلاء
    
    مفيد عند تغيير الإعدادات أو حل مشاكل
    """
    try:
        agent_manager.reset()
        
        return {
            "status": "success",
            "message": "تم إعادة تعيين نظام الوكلاء بنجاح",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في إعادة التعيين: {str(e)}"
        )
