#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
وكيل منصة X الفرعي
X Platform Sub-Agent
"""

from typing import Dict, Any, Optional
from autogen_agentchat.agents import AssistantAgent
from .tools import x_login, x_post, x_update_profile


class XAgent:
    """وكيل متخصص في إدارة منصة X (Twitter)"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        تهيئة وكيل منصة X
        
        Args:
            llm_config: إعدادات نموذج اللغة
        """
        self.llm_config = llm_config
        
        self.agent = AssistantAgent(
            name="XAgent",
            model_client=llm_config,
            system_message="""أنت وكيل متخصص في إدارة منصة X (Twitter).
            
مهامك:
1. تسجيل الدخول لحسابات X
2. نشر التغريدات
3. تحديث معلومات الملف الشخصي
4. إدارة المحتوى على X

استخدم الأدوات المتاحة لتنفيذ هذه المهام بكفاءة.""",
تحدث بالعربية مع المستخدم وكن مفيداً ودقيقاً.""",
            llm_config=llm_config,
            human_input_mode="NEVER",
            code_execution_config=False,
        )
        
        self._register_tools()
    
    def _register_tools(self):
        """تسجيل الأدوات المتاحة لوكيل X"""
        # في الإصدار الجديد، الأدوات تُستخدم مباشرة
        pass
    
    def get_agent(self) -> ConversableAgent:
        """الحصول على كائن الوكيل"""
        return self.agent
    
    def process_request(self, message: str, context: Dict[str, Any] = None) -> str:
        """
        معالجة طلب من المستخدم
        
        Args:
            message: رسالة المستخدم
            context: السياق الإضافي
            
        Returns:
            الرد من الوكيل
        """
        # معالجة مباشرة بدون استخدام الوكيل المعقد
        intent = context.get("intent") if context else None
        entities = context.get("entities", {}) if context else {}
        
        if intent == "add_account":
            username = entities.get("username")
            password = entities.get("password")
            label = entities.get("account_name", "default_account")
            
            if username and password:
                result = x_login(username, password, label)
                return result.get("message", "تم محاولة تسجيل الدخول")
            else:
                return "يرجى تقديم اسم المستخدم وكلمة المرور"
        
        elif intent == "create_post":
            content = entities.get("content")
            account = entities.get("account_name", "default_account")
            
            if content:
                result = x_post(account, content)
                return result.get("message", "تم محاولة النشر")
            else:
                return "يرجى تقديم محتوى التغريدة"
        
        elif intent == "update_profile":
            account = entities.get("account_name", "default_account")
            name = entities.get("name")
            bio = entities.get("bio")
            
            result = x_update_profile(account, name=name, bio=bio)
            return result.get("message", "تم محاولة تحديث الملف الشخصي")
        
        return f"تم استلام الطلب: {message}"
