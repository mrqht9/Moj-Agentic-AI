# 📖 دليل الاستخدام - كنق الاتمته

## 🎯 نظرة عامة

هذا التطبيق عبارة عن شات بوت ذكي مبني على:
- **Frontend**: HTML5 + TailwindCSS + JavaScript (WebSocket)
- **Backend**: FastAPI + Python 3.11+
- **AI**: OpenAI GPT-4

## 🏗️ بنية المشروع

```
Moj-Agentic-AI/
│
├── app/                          # Backend Application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app + WebSocket handler
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py             # Settings & Environment variables
│   └── services/
│       ├── __init__.py
│       └── ai_service.py         # OpenAI integration
│
├── templates/
│   └── chat.html                 # Chat interface (Arabic RTL)
│
├── static/                       # Static files (CSS, JS, images)
│
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── run.py                        # Quick start script
├── SETUP.md                      # Setup instructions
└── USAGE_GUIDE.md               # This file
```

## 🚀 التشغيل السريع

### 1. تشغيل التطبيق

```bash
python run.py
```

### 2. فتح المتصفح

```
http://localhost:8000
```

## 💬 استخدام الشات

### إرسال رسالة
1. اكتب رسالتك في صندوق الإدخال بالأسفل
2. اضغط **Enter** أو زر الإرسال ⬆️
3. انتظر رد المساعد الذكي

### مميزات الرسائل
- **نسخ الكود**: اضغط على زر "نسخ الكود" في أي كتلة كود
- **نسخ الرسالة**: اضغط على أيقونة النسخ 📋
- **إعادة التوليد**: اضغط على أيقونة التحديث 🔄
- **تقييم الرد**: اضغط على 👍 أو 👎

### محادثة جديدة
اضغط على زر ➕ في الأعلى لبدء محادثة جديدة

## 🎨 تخصيص المظهر

### تبديل الوضع الليلي/النهاري
اضغط على زر 🌙 في الشريط الجانبي

### تعديل الألوان
عدّل ملف `templates/chat.html` في قسم `tailwind.config`:

```javascript
colors: {
    "primary": "#0db9f2",           // اللون الأساسي
    "background-light": "#f5f8f8",  // خلفية الوضع النهاري
    "background-dark": "#101e22",   // خلفية الوضع الليلي
}
```

## ⚙️ التكوين المتقدم

### تعديل إعدادات OpenAI

في ملف `.env`:

```env
# نموذج GPT (gpt-4, gpt-3.5-turbo, gpt-4-turbo)
OPENAI_MODEL=gpt-4

# الحد الأقصى للتوكنز (100-4000)
OPENAI_MAX_TOKENS=2000

# درجة الإبداع (0.0-2.0)
# 0.0 = ردود دقيقة ومتوقعة
# 2.0 = ردود إبداعية ومتنوعة
OPENAI_TEMPERATURE=0.7
```

### تعديل منفذ الخادم

في ملف `.env`:
```env
PORT=8000
HOST=0.0.0.0
```

أو في `run.py`:
```python
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=8080,  # غيّر المنفذ هنا
    reload=True
)
```

## 🔌 API Documentation

### WebSocket Endpoint

**URL**: `ws://localhost:8000/ws/chat`

**إرسال رسالة**:
```json
{
    "message": "مرحباً، كيف حالك؟"
}
```

**استقبال الردود**:

1. **رسالة المستخدم**:
```json
{
    "type": "user_message",
    "message": "مرحباً، كيف حالك؟",
    "timestamp": "2024-01-08T19:24:00"
}
```

2. **مؤشر الكتابة**:
```json
{
    "type": "typing",
    "status": true
}
```

3. **رد المساعد**:
```json
{
    "type": "assistant_message",
    "message": "مرحباً! أنا بخير، شكراً...",
    "timestamp": "2024-01-08T19:24:05"
}
```

4. **رسالة خطأ**:
```json
{
    "type": "error",
    "message": "حدث خطأ في الاتصال",
    "timestamp": "2024-01-08T19:24:05"
}
```

### HTTP Endpoints

#### GET /
يعرض واجهة الشات

#### GET /health
فحص صحة الخادم

**Response**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-08T19:24:00"
}
```

## 🛠️ التطوير

### إضافة ميزة جديدة

#### 1. إضافة خدمة AI جديدة

أنشئ ملف في `app/services/`:

```python
# app/services/custom_service.py
class CustomService:
    def __init__(self):
        pass
    
    async def process(self, data):
        # معالجة البيانات
        return result
```

#### 2. إضافة endpoint جديد

في `app/main.py`:

```python
@app.get("/api/custom")
async def custom_endpoint():
    return {"message": "Custom endpoint"}
```

#### 3. تعديل الواجهة

عدّل `templates/chat.html` حسب الحاجة.

### تشغيل في وضع التطوير

```bash
uvicorn app.main:app --reload --log-level debug
```

## 🔐 الأمان

### حماية API Key
- ✅ استخدم ملف `.env` لتخزين المفاتيح
- ✅ لا ترفع ملف `.env` إلى Git
- ✅ استخدم `.gitignore` لحماية الملفات الحساسة

### HTTPS في الإنتاج
استخدم Nginx أو Caddy كـ reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📊 المراقبة والتسجيل

### عرض Logs

```bash
# في Terminal حيث يعمل التطبيق
# سترى logs تلقائياً
```

### تفعيل Debug Mode

في `.env`:
```env
DEBUG=True
```

## 🐛 استكشاف الأخطاء

### خطأ: "Connection refused"
- تأكد من تشغيل الخادم
- تأكد من المنفذ 8000 غير محجوب

### خطأ: "Invalid API Key"
- تأكد من صحة `OPENAI_API_KEY` في `.env`
- تأكد من وجود رصيد في حساب OpenAI

### خطأ: "Module not found"
```bash
pip install -r requirements.txt
```

### WebSocket لا يعمل
- افحص Console المتصفح (F12)
- تأكد من عدم وجود Firewall يحجب WebSocket
- تأكد من استخدام البروتوكول الصحيح (ws:// أو wss://)

## 📱 الاستخدام على الهاتف

التطبيق responsive ويعمل على:
- 📱 الهواتف الذكية
- 💻 الأجهزة اللوحية
- 🖥️ أجهزة الكمبيوتر

للوصول من الهاتف:
1. تأكد من اتصال الهاتف بنفس الشبكة
2. اعرف IP الكمبيوتر: `ipconfig` (Windows) أو `ifconfig` (Linux/Mac)
3. افتح المتصفح على: `http://192.168.x.x:8000`

## 🚀 النشر (Deployment)

### Docker (قريباً)
```bash
docker build -t chatbot .
docker run -p 8000:8000 chatbot
```

### Heroku
```bash
heroku create
git push heroku main
```

### Railway / Render
اتبع التعليمات على المنصة المختارة.

## 📞 الدعم والمساعدة

### الموارد
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)

### المساهمة
المساهمات مرحب بها! يرجى:
1. Fork المشروع
2. إنشاء branch جديد
3. عمل commit للتغييرات
4. إرسال Pull Request

---

**صُنع بـ ❤️ في السعودية**
