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
        
        result = agent_manager.process_user_message(
            message=request.message,
            user_id=user_id
        )
        
        # معالجة الحالة التي يرجع فيها result = None
        if result is None:
            result = {
                "success": False,
                "message": "عذراً، لم أتمكن من معالجة طلبك. يرجى إعادة صياغته.",
                "intent_result": None,
                "agent": None,
                "action": None
            }
        
        return AgentMessageResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            intent_result=result.get("intent_result"),
            agent=result.get("agent"),
            action=result.get("action"),
            timestamp=datetime.now().isoformat()
        )
    
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
