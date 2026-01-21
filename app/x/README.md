# X Suite (Dashboard + API)

نظام موحّد لإدارة حسابات X عبر Playwright:
- تسجيل دخول وحفظ الكوكيز باسم الحساب داخل مجلد واحد `cookies/`
- نشر منشورات (مع/بدون ميديا) مع اختيار ملف الكوكيز
- تعديل البروفايل (اسم/بايو/موقع/رابط + صور Avatar/Banner) مع اختيار ملف الكوكيز
- Dashboard احترافي + سجل عمليات + قاعدة بيانات SQLite
- REST API محمية بتوكن (Bearer)

## التشغيل السريع

### 1) إنشاء بيئة وتثبيت المتطلبات

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
playwright install
```

> ملاحظة: إن كنت تريد تشغيل Chrome Channel تحديداً:
> - ثبّت Chrome على جهازك
> - عرّف المتغير: `XSUITE_CHROME_CHANNEL=chrome`

### 2) إعداد المتغيرات (اختياري)

انسخ ملف `.env.example` إلى `.env` وعدّل القيم.

### 3) التشغيل

```bash
python app.py
```

ثم افتح:
- Dashboard: `http://127.0.0.1:5789`

## حساب دخول لوحة التحكم
افتراضياً:
- المستخدم: `admin`
- كلمة المرور: `admin`

غيّرها عبر المتغيرات:
- `XSUITE_ADMIN_USER`
- `XSUITE_ADMIN_PASS`

## مسار الكوكيز
- جميع ملفات الكوكيز تُحفظ هنا: `cookies/`
- كل ملف باسم الحساب (label) مثل: `myacc.json`

## API
كل طلب API يحتاج هيدر:

`Authorization: Bearer your-secure-token-here`

يمكن ضبط التوكنز (مفصولة بفواصل) عبر:
- `XSUITE_API_TOKENS=token1,token2`

### أهم Endpoints
- `GET /api/health`
- `GET /api/cookies`
- `POST /api/cookies/upload` (multipart: `label`, `file`)
- `POST /api/login` (json: `label`,`username`,`password`,`headless`)
- `POST /api/post` (json أو multipart)
- `POST /api/profile/update` (multipart)
- `GET /api/stats`
- `GET /api/logs`
- `GET /api/task/<id>`

## ملاحظات مهمة
- هذا النظام يستخدم Playwright؛ وجود حماية/تحقق إضافي من X قد يتطلب تدخل يدوي.
- ملفات الكوكيز يجب أن تكون بصيغة Playwright `storage_state`.
