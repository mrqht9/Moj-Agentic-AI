#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
كنق الاتمته - Chatbot Runner
تشغيل سريع للتطبيق
"""
import os
import sys

# Fix encoding for Windows console - MUST be done first
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
    else:
        # Fallback for older Python versions
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Set environment variable for UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    print("=" * 60)
    print("كنق الاتمته - Chatbot Interface")
    print("=" * 60)
    print("Starting server...")
    print("URL: http://localhost:3000")
    print("تأكد من إضافة OPENAI_API_KEY في ملف .env")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=3000,
        reload=True,
        log_level="info"
    )
