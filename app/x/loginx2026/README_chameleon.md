# Chameleon Login - متطلبات التثبيت والتشغيل

## 📋 المتطلبات (Requirements)

### Python Version
- **Python 3.8 أو أحدث**

### المكتبات المطلوبة
```bash
pip install curl-cffi>=0.6.0
```

### ملف المتطلبات الكامل
```txt
curl-cffi>=0.6.0
```

---

## 🚀 طريقة التثبيت

### 1. تثبيت المكتبات
```bash
# الطريقة المباشرة
pip install curl-cffi>=0.6.0

# أو باستخدام ملف المتطلبات
pip install -r chameleon_requirements.txt
```

### 2. هيكل المجلدات
```
your_project/
├── chameleon_login.py          # الملف الرئيسي
├── x_auth/                     # مجلد x_auth
│   ├── castle.py              # Castle Token
│   ├── login.py               # Login functions
│   └── transaction.py         # Client Transaction
├── chameleon_requirements.txt  # المتطلبات
└── cookies/                   # مجلد حفظ الكوكيز (يُنشأ تلقائياً)
```

---

## 🛠️ المتطلبات الإضافية

### ملفات x_auth المطلوبة
يجب أن يحتوي مجلد `x_auth/` على:
- `castle.py` - لتوليد Castle Token
- `login.py` - دوال تسجيل الدخول
- `transaction.py` - Client Transaction

### صلاحيات النظام
- لا يتطلب صلاحيات admin
- يعمل على Windows/MacOS/Linux

---

## 🎯 طريقة التشغيل

### 1. التشغيل المباشر
```bash
python chameleon_login.py
```

### 2. المتطلبات عند التشغيل
- اتصال بالإنترنت
- اسم مستخدم وكلمة مرور تويتر صالحين

---

## 📝 ملاحظات هامة

### المكتبات المعتمدة
- **curl-cffi**: المحاكاة المتقدمة للمتصفحات
- **Standard Library**: جميع المكتبات الأخرى من المكتبة القياسية بايثون

### التوافق
- **Windows**: ✅ مدعوم بالكامل
- **MacOS**: ✅ مدعوم بالكامل  
- **Linux**: ✅ مدعوم بالكامل

### الأداء
- يستخدم محاكاة متقدمة للمتصفحات
- بصمات متغيرة لكل طلب
- معالجة غير متزامنة (async)

---

## 🔧 استكشاف الأخطاء

### مشاكل شائعة
1. **curl-cffi not installed**: قم بتثبيت المكتبة
2. **Python version**: تأكد من استخدام Python 3.8+
3. **x_auth missing**: تأكد من وجود مجلد x_auth

### حلول سريعة
```bash
# تحديث curl-cffi
pip install curl-cffi --upgrade

# تثبيت جميع المتطلبات
pip install -r chameleon_requirements.txt
```

---

## 💡 معلومات إضافية

- لا يتطلب متصفح حقيقي
- يعتمد على محاكاة curl_cffi
- يدعم Chrome, Firefox, Edge
- بصمات متغيرة تلقائياً
