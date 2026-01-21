#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
إعدادات نظام الوكلاء
Agents Configuration
"""

import os
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# مسار ملف الإعدادات
BASE_DIR = Path(__file__).resolve().parent.parent.parent
AGENTS_ENV_FILE = BASE_DIR / ".env.agents"


def get_llm_config() -> Dict[str, Any]:
    """
    الحصول على إعدادات LLM - مبسطة للإصدار الجديد
    
    Returns:
        قاموس إعدادات LLM
    """
    load_dotenv(AGENTS_ENV_FILE)
    
    api_type = os.getenv("LLM_API_TYPE", "openai")
    
    if api_type == "openai":
        return {
            "model": os.getenv("OPENAI_MODEL", "gpt-4"),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
        }
    
    elif api_type == "azure":
        return {
            "config_list": [
                {
                    "model": os.getenv("AZURE_OPENAI_MODEL", "gpt-4"),
                    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                    "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),
                    "api_type": "azure",
                    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                }
            ],
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "timeout": int(os.getenv("LLM_TIMEOUT", "120")),
        }
    
    elif api_type == "ollama":
        return {
            "config_list": [
                {
                    "model": os.getenv("OLLAMA_MODEL", "llama2"),
                    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                    "api_key": "ollama",
                }
            ],
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "timeout": int(os.getenv("LLM_TIMEOUT", "120")),
        }
    
    elif api_type == "lmstudio":
        return {
            "config_list": [
                {
                    "model": os.getenv("LMSTUDIO_MODEL", "local-model"),
                    "base_url": os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
                    "api_key": "lm-studio",
                }
            ],
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "timeout": int(os.getenv("LLM_TIMEOUT", "120")),
        }
    
    else:
        raise ValueError(f"نوع API غير مدعوم: {api_type}")


def get_agent_settings() -> Dict[str, Any]:
    """
    إعدادات عامة للوكلاء
    
    Returns:
        إعدادات الوكلاء
    """
    return {
        "max_consecutive_auto_reply": int(os.getenv("AGENT_MAX_REPLIES", "10")),
        "human_input_mode": os.getenv("AGENT_HUMAN_INPUT_MODE", "NEVER"),
        "code_execution_config": False,
    }
