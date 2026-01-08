#!/usr/bin/env python
"""
كنق الاتمته - Chatbot Runner
تشغيل سريع للتطبيق
"""
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 كنق الاتمته - Chatbot Interface")
    print("=" * 60)
    print("🚀 Starting server...")
    print("📍 URL: http://localhost:8000")
    print("⚠️  تأكد من إضافة OPENAI_API_KEY في ملف .env")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
