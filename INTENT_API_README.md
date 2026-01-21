# 🎯 Intent API - دليل الاستخدام في n8n

## 📋 نظرة عامة

نظام Intent API يتيح لك التعرف على نوايا المستخدم من النصوص العربية والإنجليزية، واستخراج الكيانات المهمة، وتحديد المنصة المستهدفة.

## 🚀 البدء السريع

### 1. تشغيل الخادم

```bash
cd c:\Users\engsa\Desktop\mojv1
python app/main.py
```

الخادم سيعمل على: `http://localhost:5789`

### 2. اختبار API

```bash
python test_intent_api.py
```

---

## 📡 API Endpoints

### 1️⃣ التعرف على النية (Detect Intent)

**Endpoint:** `POST /api/intent/detect`

**الاستخدام في n8n:**
- أضف node من نوع **HTTP Request**
- Method: `POST`
- URL: `http://localhost:5789/api/intent/detect`
- Body Type: `JSON`

**Body:**
```json
{
  "text": "أضف حساب تويتر الخاص بي",
  "context": {},
  "user_id": 1
}
```

**Response:**
```json
{
  "intent": "add_account",
  "confidence": 0.95,
  "entities": {},
  "platform": "twitter",
  "raw_text": "أضف حساب تويتر الخاص بي",
  "timestamp": "2024-01-21T22:44:00",
  "suggestions": [
    "قم بتوفير بيانات الاعتماد للحساب",
    "اختر المنصة: Twitter, Instagram, Facebook, LinkedIn"
  ]
}
```

---

### 2️⃣ قائمة النوايا المدعومة (List Intents)

**Endpoint:** `GET /api/intent/list`

**الاستخدام في n8n:**
- أضف node من نوع **HTTP Request**
- Method: `GET`
- URL: `http://localhost:5789/api/intent/list`

**Response:**
```json
{
  "intents": [
    {
      "intent": "add_account",
      "description": "إضافة حساب جديد على منصة التواصل",
      "category": "account_management"
    },
    {
      "intent": "create_post",
      "description": "إنشاء ونشر منشور جديد",
      "category": "content_management"
    }
  ],
  "platforms": ["twitter", "x", "instagram", "facebook", "linkedin", "tiktok"]
}
```

---

### 3️⃣ الاقتراحات (Suggestions)

**Endpoint:** `POST /api/intent/suggestions`

**Body:**
```json
{
  "partial_text": "أضف"
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "intent": "add_account",
      "example": "أضف حساب",
      "description": "إضافة حساب جديد على منصة التواصل"
    }
  ]
}
```

---

### 4️⃣ معالجة دفعات (Batch Detection)

**Endpoint:** `POST /api/intent/batch`

**Body:**
```json
[
  {
    "text": "أضف حساب تويتر",
    "user_id": 1
  },
  {
    "text": "انشر منشور على انستقرام",
    "user_id": 1
  }
]
```

---

## 🔧 إعداد Workflow في n8n

### Workflow مقترح:

```
1. [Webhook] استقبال الرسالة
   ↓
2. [HTTP Request] التعرف على النية
   POST http://localhost:5789/api/intent/detect
   Body: {"text": "={{$json.message}}", "user_id": 1}
   ↓
3. [Switch] توجيه حسب النية
   - Case 1: intent = "add_account" → إضافة حساب
   - Case 2: intent = "create_post" → إنشاء منشور
   - Case 3: intent = "schedule_post" → جدولة منشور
   - Case 4: intent = "get_analytics" → عرض إحصائيات
   ↓
4. [Function] تنفيذ الإجراء المناسب
   ↓
5. [Respond to Webhook] إرسال الرد
```

---

## 📊 النوايا المدعومة

### 🔐 إدارة الحسابات
- `add_account` - إضافة حساب
- `remove_account` - حذف حساب
- `list_accounts` - عرض الحسابات
- `switch_account` - التبديل بين الحسابات

### 📝 إدارة المحتوى
- `create_post` - إنشاء منشور
- `schedule_post` - جدولة منشور
- `delete_post` - حذف منشور
- `edit_post` - تعديل منشور

### 📈 التحليلات
- `get_analytics` - عرض الإحصائيات
- `get_engagement` - معدل التفاعل
- `get_followers` - عدد المتابعين

### 💬 التفاعل
- `reply_to_comment` - الرد على تعليق
- `like_post` - الإعجاب بمنشور
- `share_post` - مشاركة منشور

### 🤖 الأتمتة
- `create_automation` - إنشاء أتمتة
- `manage_automation` - إدارة الأتمتة

### 🆘 عام
- `help` - المساعدة
- `greeting` - تحية

---

## 🌐 المنصات المدعومة

- Twitter / X
- Instagram
- Facebook
- LinkedIn
- TikTok

---

## 💡 أمثلة الاستخدام

### مثال 1: إضافة حساب تويتر

**Input:**
```json
{
  "text": "أضف حساب تويتر الخاص بي"
}
```

**Output:**
```json
{
  "intent": "add_account",
  "confidence": 0.95,
  "platform": "twitter",
  "suggestions": [
    "قم بتوفير بيانات الاعتماد للحساب"
  ]
}
```

### مثال 2: نشر تغريدة

**Input:**
```json
{
  "text": "انشر 'مرحباً بالجميع!' على تويتر"
}
```

**Output:**
```json
{
  "intent": "create_post",
  "confidence": 0.95,
  "platform": "twitter",
  "entities": {
    "post_content": "مرحباً بالجميع!"
  }
}
```

### مثال 3: جدولة منشور

**Input:**
```json
{
  "text": "جدول منشور على انستقرام غداً الساعة 10 صباحاً"
}
```

**Output:**
```json
{
  "intent": "schedule_post",
  "confidence": 0.95,
  "platform": "instagram",
  "entities": {
    "schedule_time": {
      "type": "tomorrow",
      "value": "غداً"
    }
  }
}
```

---

## 🔑 استخدام المتغيرات في n8n

في n8n، يمكنك الوصول إلى البيانات المُرجعة باستخدام:

```javascript
// النية المكتشفة
{{$json.intent}}

// مستوى الثقة
{{$json.confidence}}

// المنصة
{{$json.platform}}

// الكيانات المستخرجة
{{$json.entities}}

// الاقتراحات
{{$json.suggestions}}

// النص الأصلي
{{$json.raw_text}}
```

---

## 🎨 مثال Switch Node في n8n

```javascript
// في Switch node، استخدم:
// Mode: Expression

// Rule 1 - إضافة حساب
{{$json.intent}} === "add_account"

// Rule 2 - إنشاء منشور
{{$json.intent}} === "create_post"

// Rule 3 - جدولة منشور
{{$json.intent}} === "schedule_post"

// Rule 4 - إحصائيات
{{$json.intent}} === "get_analytics"
```

---

## ⚠️ ملاحظات مهمة

1. **تأكد من تشغيل الخادم** قبل استخدام API في n8n
2. **مستوى الثقة** (confidence) يتراوح من 0 إلى 1
3. **الكيانات** (entities) قد تكون فارغة إذا لم يتم استخراج أي معلومات
4. **المنصة** (platform) قد تكون null إذا لم يتم تحديد منصة في النص

---

## 🐛 استكشاف الأخطاء

### الخادم لا يعمل
```bash
# تحقق من أن الخادم يعمل
curl http://localhost:5789/health
```

### خطأ في الاتصال من n8n
- تأكد من أن n8n و API على نفس الشبكة
- استخدم `http://localhost:5789` إذا كان n8n على نفس الجهاز
- استخدم IP الجهاز إذا كان n8n على جهاز آخر

---

## 📞 الدعم

للمزيد من المعلومات، راجع:
- `test_intent_api.py` - أمثلة الاختبار
- `n8n_intent_examples.json` - أمثلة n8n
- `app/api/intent_routes.py` - كود API

---

## ✅ جاهز للاستخدام!

الآن يمكنك استخدام Intent API في n8n workflows الخاصة بك! 🎉
