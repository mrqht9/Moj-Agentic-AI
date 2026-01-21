@echo off
echo ========================================
echo    تشغيل الشاتبوت مع نظام الوكلاء
echo ========================================
echo.

echo [1/2] تحميل المتغيرات البيئية...
if exist .env.agents (
    echo ✓ ملف .env.agents موجود
) else (
    echo ✗ ملف .env.agents غير موجود!
    echo انسخ .env.agents وعدل الإعدادات
    pause
    exit
)

echo.
echo [2/2] تشغيل الخادم...
echo.
echo ========================================
echo   الشاتبوت يعمل على:
echo   http://localhost:5789
echo ========================================
echo.

python app/main.py

pause
