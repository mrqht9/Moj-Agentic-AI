#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
مدير الوكلاء
Agent Manager - Singleton pattern
"""

from typing import Dict, Any, Optional
from .config import get_llm_config
from .main_agent_simple import MainAgent


class AgentManager:
    """مدير الوكلاء - نمط Singleton"""
    
    _instance: Optional['AgentManager'] = None
    _main_agent: Optional[MainAgent] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, llm_config: Optional[Dict[str, Any]] = None):
        """
        تهيئة نظام الوكلاء
        
        Args:
            llm_config: إعدادات LLM (اختياري)
        """
        if self._main_agent is None:
            if llm_config is None:
                llm_config = get_llm_config()
            
            self._main_agent = MainAgent(llm_config)
    
    def get_main_agent(self) -> MainAgent:
        """
        الحصول على الوكيل الرئيسي
        
        Returns:
            الوكيل الرئيسي
        """
        if self._main_agent is None:
            self.initialize()
        
        return self._main_agent
    
    def process_user_message(
        self, 
        message: str, 
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        معالجة رسالة من المستخدم
        
        Args:
            message: رسالة المستخدم
            user_id: معرف المستخدم
            session_id: معرف الجلسة
            db: جلسة قاعدة البيانات
            
        Returns:
            الرد من النظام
        """
        main_agent = self.get_main_agent()
        return main_agent.process_message(message, user_id, session_id, db)
    
    def reset(self):
        """إعادة تعيين نظام الوكلاء"""
        self._main_agent = None


agent_manager = AgentManager()
