# 🔗 دليل تكامل n8n Webhook

هذا الدليل يشرح كيفية تكامل Moj AI مع n8n من خلال webhooks.

## 📋 نظرة عامة

تم إضافة دعم كامل لإرسال رسائل المستخدمين تلقائياً إلى n8n webhook. كل رسالة يرسلها المستخدم في الشات بوت يتم إرسالها تلقائياً إلى n8n للمعالجة.

## ⚙️ الإعداد

### 1. إعداد متغيرات البيئة

أضف الإعدادات التالية إلى ملف `.env`:

```env
# N8N Webhook Configuration
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id
N8N_WEBHOOK_ENABLED=true
```

**ملاحظات:**
- `N8N_WEBHOOK_URL`: عنوان webhook الخاص بك في n8n
- `N8N_WEBHOOK_ENABLED`: `true` لتفعيل الإرسال، `false` لإيقافه

### 2. الحصول على n8n Webhook URL

1. افتح n8n
2. أنشئ workflow جديد
3. أضف node من نوع "Webhook"
4. اضغط على "Execute Workflow" للحصول على Webhook URL
5. انسخ الـ URL وأضفه في `.env`

## 📨 تنسيق البيانات المرسلة

عند إرسال رسالة من المستخدم، يتم إرسال البيانات التالية إلى n8n:

```json
{
  "message": "نص الرسالة التي أرسلها المستخدم",
  "timestamp": "2026-01-08T20:30:00.000000",
  "source": "moj_ai_chatbot",
  "type": "user_message",
  "session_id": "session_id_optional",
  "user_id": "user_id_optional",
  "metadata": {
    "source": "websocket"
  }
}
```

### الحقول:

| الحقل | النوع | الوصف |
|-------|------|-------|
| `message` | string | الرسالة التي أرسلها المستخدم (مطلوب) |
| `timestamp` | string | وقت الإرسال بصيغة ISO 8601 |
| `source` | string | المصدر (دائماً "moj_ai_chatbot") |
| `type` | string | نوع الرسالة ("user_message") |
| `session_id` | string (اختياري) | معرف الجلسة |
| `user_id` | string (اختياري) | معرف المستخدم |
| `metadata` | object (اختياري) | بيانات إضافية |

## 🚀 الاستخدام

### 1. إرسال تلقائي عبر WebSocket

عند استخدام واجهة الشات (WebSocket)، يتم إرسال الرسائل تلقائياً إلى n8n:

```javascript
// في الواجهة الأمامية (WebSocket)
const message = {
  message: "مرحباً",
  session_id: "session_123",
  user_id: "user_456"
};
websocket.send(JSON.stringify(message));
```

### 2. إرسال مباشر عبر API

يمكنك أيضاً إرسال رسائل مباشرة عبر POST endpoint:

```bash
curl -X POST http://localhost:3000/api/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "مرحباً من API",
    "session_id": "session_123",
    "user_id": "user_456"
  }'
```

**Response:**

```json
{
  "status": "success",
  "message": "تم إرسال الرسالة إلى n8n بنجاح",
  "timestamp": "2026-01-08T20:30:00.000000"
}
```

## 🔧 إعداد n8n Workflow

### مثال بسيط:

1. **Webhook Node:**
   - Method: POST
   - Path: `/your-webhook-path`

2. **Function Node (معالجة البيانات):**
   ```javascript
   const message = $input.item.json.message;
   const timestamp = $input.item.json.timestamp;
   
   return {
     processedMessage: message.toUpperCase(),
     receivedAt: timestamp
   };
   ```

3. **HTTP Request Node (اختياري):**
   - يمكنك إرسال استجابة أو حفظ البيانات

### مثال متقدم مع معالجة الرسائل:

```javascript
// في Function Node
const data = $input.item.json;

// معالجة الرسالة
const processedData = {
  originalMessage: data.message,
  cleanedMessage: data.message.trim(),
  wordCount: data.message.split(' ').length,
  timestamp: data.timestamp,
  sessionId: data.session_id || 'unknown',
  userId: data.user_id || 'anonymous'
};

return processedData;
```

## 📊 Endpoints المتاحة

### POST /api/send-message

إرسال رسالة مباشرة إلى n8n webhook.

**Request Body:**
```json
{
  "message": "النص المطلوب إرساله",
  "session_id": "optional_session_id",
  "user_id": "optional_user_id",
  "metadata": {
    "key": "value"
  }
}
```

**Response:**
- `200`: تم الإرسال بنجاح
- `503`: فشل الإرسال (webhook معطّل أو غير متاح)
- `500`: خطأ في الخادم

## 🐛 حل المشاكل

### المشكلة: الرسائل لا تصل إلى n8n

**الحل:**
1. تحقق من `N8N_WEBHOOK_ENABLED=true` في `.env`
2. تأكد من صحة `N8N_WEBHOOK_URL`
3. تحقق من أن n8n workflow نشط
4. راجع logs للتأكد من الأخطاء

### المشكلة: timeout errors

**الحل:**
- تأكد من أن n8n متاح ومتصل
- زد timeout في `webhook_service.py` إذا لزم الأمر
- تحقق من سرعة الاتصال بالإنترنت

### المشكلة: 404 Not Found

**الحل:**
- تأكد من صحة webhook URL
- تأكد من أن workflow في n8n نشط
- تحقق من path في webhook node

## 📝 أمثلة استخدام

### مثال 1: حفظ الرسائل في قاعدة بيانات

في n8n، استخدم:
1. Webhook node (استقبال البيانات)
2. PostgreSQL node (حفظ في قاعدة البيانات)

### مثال 2: إرسال إشعارات

في n8n، استخدم:
1. Webhook node
2. Slack/Telegram/Discord node (إرسال إشعارات)

### مثال 3: معالجة وتحليل

في n8n، استخدم:
1. Webhook node
2. Function node (معالجة البيانات)
3. OpenAI node (تحليل إضافي)
4. Save to database

## 🔐 الأمان

- تأكد من استخدام HTTPS في production
- يمكنك إضافة authentication في n8n webhook
- استخدم environment variables لحفظ معلومات حساسة

## 📚 موارد إضافية

- [n8n Documentation](https://docs.n8n.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Webhook Best Practices](https://docs.n8n.io/workflows/webhooks/)

---

**تم الإنشاء بواسطة Moj AI Team**
