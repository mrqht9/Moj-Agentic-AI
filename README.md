# 🤖 Moj AI - Agentic AI Social Media Management System v2.0

<div dir="rtl">

# موج AI - نظام إدارة وسائل التواصل الاجتماعي بالذكاء الاصطناعي الإجرائي

نظام متكامل لإدارة وسائل التواصل الاجتماعي باستخدام الذكاء الاصطناعي، مبني على FastAPI و OpenAI GPT مع دعم كامل للواجهة العربية.

</div>

## 🌟 Features / المميزات

### Core Features
- 🤖 **AI-Powered Chatbot** - Intelligent conversational AI using OpenAI GPT-4
- 💬 **Real-time WebSocket Communication** - Instant messaging with WebSocket
- 🌐 **Arabic RTL Support** - Full Arabic interface with RTL layout
- 🌓 **Dark/Light Mode** - Beautiful dark and light themes
- 📱 **Responsive Design** - Works on all devices (desktop, tablet, mobile)
- ⚡ **High Performance** - Built with FastAPI for optimal speed

### Advanced Capabilities (Planned)
- 🔄 **Social Media Automation** - Twitter, Instagram, YouTube, TikTok integration
- 🌐 **Browser Automation** - Playwright for web scraping and automation
- 🎥 **Media Processing** - Video, audio, and image processing with OpenCV
- 🔐 **Secure Authentication** - JWT-based authentication system
- 📊 **Data Analytics** - Advanced analytics and reporting
- ⚙️ **Task Queue** - Celery for background job processing

<div dir="rtl">

### المميزات الأساسية
- 🤖 **شات بوت ذكي** - ذكاء اصطناعي محادث باستخدام OpenAI GPT-4
- 💬 **اتصال WebSocket مباشر** - رسائل فورية مع WebSocket
- 🌐 **دعم العربية RTL** - واجهة عربية كاملة مع تخطيط من اليمين لليسار
- 🌓 **الوضع الليلي/النهاري** - ثيمات جميلة للوضع الليلي والنهاري
- 📱 **تصميم متجاوب** - يعمل على جميع الأجهزة
- ⚡ **أداء عالي** - مبني على FastAPI للأداء الأمثل

### الإمكانيات المتقدمة (مخطط لها)
- 🔄 **أتمتة وسائل التواصل** - تكامل مع Twitter, Instagram, YouTube, TikTok
- 🌐 **أتمتة المتصفح** - Playwright للكشط والأتمتة
- 🎥 **معالجة الوسائط** - معالجة الفيديو والصوت والصور مع OpenCV
- 🔐 **المصادقة الآمنة** - نظام مصادقة يعتمد على JWT
- 📊 **تحليل البيانات** - تحليلات وتقارير متقدمة
- ⚙️ **قائمة المهام** - Celery لمعالجة المهام في الخلفية

</div>

## 📋 Requirements / المتطلبات

- Python 3.11 or higher
- OpenAI API Key (Get one at [platform.openai.com](https://platform.openai.com/api-keys))
- PostgreSQL (optional, for database features)
- MongoDB (optional, for NoSQL storage)
- Redis (optional, for caching and task queue)

<div dir="rtl">

- Python 3.11 أو أحدث
- مفتاح OpenAI API (احصل عليه من [platform.openai.com](https://platform.openai.com/api-keys))
- PostgreSQL (اختياري، للميزات القاعدة البيانات)
- MongoDB (اختياري، للتخزين NoSQL)
- Redis (اختياري، للتخزين المؤقت وقائمة المهام)

</div>

## 🚀 Quick Start / البدء السريع

### Installation / التثبيت

1. **Clone the repository / استنساخ المستودع:**

```bash
git clone https://github.com/Mrsos07/Moj-Agentic-AI.git
cd Moj-Agentic-AI
```

2. **Create virtual environment / إنشاء بيئة افتراضية:**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies / تثبيت المتطلبات:**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Install Playwright browsers (Required) / تثبيت متصفحات Playwright (مطلوب):**

```bash
playwright install
```

5. **Setup environment variables / إعداد متغيرات البيئة:**

Create a `.env` file in the root directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.7

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Database (Optional)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=moj_ai_db

# MongoDB (Optional)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=moj_ai_db

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

<div dir="rtl">

أنشئ ملف `.env` في المجلد الرئيسي:

</div>

6. **Run the application / تشغيل التطبيق:**

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

7. **Open in browser / فتح في المتصفح:**

**Backend API:** http://localhost:8000

**Frontend (React):** http://localhost:3000 (see Frontend Setup section)

<div dir="rtl">

**واجهة الخادم (API):** http://localhost:8000

**الواجهة الأمامية (React):** http://localhost:3000 (راجع قسم إعداد الواجهة الأمامية)

</div>

## 📁 Project Structure / بنية المشروع

```
Moj-Agentic-AI/
├── app/                          # Backend Application (FastAPI)
│   ├── __init__.py
│   ├── main.py                   # FastAPI application & WebSocket handler
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py             # Configuration settings
│   └── services/
│       ├── __init__.py
│       └── ai_service.py         # OpenAI integration service
├── frontend/                     # React Frontend Application
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── MessageList.jsx
│   │   │   ├── Message.jsx
│   │   │   ├── MessageInput.jsx
│   │   │   └── TypingIndicator.jsx
│   │   ├── App.jsx               # Main React component
│   │   ├── main.jsx              # Entry point
│   │   └── index.css             # Tailwind styles
│   ├── index.html
│   ├── package.json              # Node.js dependencies
│   ├── vite.config.js            # Vite configuration
│   ├── tailwind.config.js        # Tailwind configuration
│   ├── postcss.config.js         # PostCSS configuration
│   └── README.md                 # Frontend documentation
├── templates/
│   └── chat.html                 # Legacy HTML interface
├── static/                       # Static files (CSS, JS, images)
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── run.py                        # Backend quick start script
├── SETUP.md                      # Detailed setup guide
├── USAGE_GUIDE.md               # Usage guide
└── README.md                     # This file
```

## 🎨 Frontend (React + Vite + TailwindCSS)

### Technology Stack
- **React 18.2.0** - Modern UI library
- **Vite 5.0.8** - Fast build tool and dev server
- **TailwindCSS 3.4.1** - Utility-first CSS framework
- **Axios 1.6.5** - HTTP client for API calls
- **React Icons 5.0.1** - Icon library (FiSend, FiPlus, MdDashboard, etc.)

### Frontend Features
- ✨ **Modern React Components** - Modular and reusable components
- 🎨 **TailwindCSS Styling** - Beautiful and responsive design
- 🌓 **Dark/Light Mode** - Toggle between themes
- 📱 **Fully Responsive** - Works on all screen sizes
- ⚡ **Fast Development** - Vite HMR for instant updates
- 🔌 **WebSocket Integration** - Real-time chat with backend
- 🎯 **Arabic RTL Support** - Full right-to-left layout

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install Node.js dependencies:**
```bash
npm install
```

3. **Run development server:**
```bash
npm run dev
```

Frontend will be available at: **http://localhost:3000**

4. **Build for production:**
```bash
npm run build
```

### Frontend Scripts
```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Lint code
```

<div dir="rtl">

## 🎨 الواجهة الأمامية (React + Vite + TailwindCSS)

### التقنيات المستخدمة
- **React 18.2.0** - مكتبة واجهة مستخدم حديثة
- **Vite 5.0.8** - أداة بناء وخادم تطوير سريع
- **TailwindCSS 3.4.1** - إطار عمل CSS
- **Axios 1.6.5** - عميل HTTP للاتصال بالـ API
- **React Icons 5.0.1** - مكتبة الأيقونات

### مميزات الواجهة الأمامية
- ✨ **مكونات React حديثة** - مكونات معيارية وقابلة لإعادة الاستخدام
- 🎨 **تصميم TailwindCSS** - تصميم جميل ومتجاوب
- 🌓 **الوضع الليلي/النهاري** - التبديل بين الثيمات
- 📱 **متجاوب بالكامل** - يعمل على جميع أحجام الشاشات
- ⚡ **تطوير سريع** - Vite HMR للتحديثات الفورية
- 🔌 **تكامل WebSocket** - دردشة فورية مع الخادم
- 🎯 **دعم العربية RTL** - تخطيط كامل من اليمين لليسار

### إعداد الواجهة الأمامية

1. **الانتقال إلى مجلد frontend:**
```bash
cd frontend
```

2. **تثبيت مكتبات Node.js:**
```bash
npm install
```

3. **تشغيل خادم التطوير:**
```bash
npm run dev
```

الواجهة الأمامية ستكون متاحة على: **http://localhost:3000**

4. **البناء للإنتاج:**
```bash
npm run build
```

### أوامر الواجهة الأمامية
```bash
npm run dev      # تشغيل خادم التطوير
npm run build    # البناء للإنتاج
npm run preview  # معاينة بناء الإنتاج
npm run lint     # فحص الكود
```

</div>

## 🔌 API Endpoints

### WebSocket
- `ws://localhost:8000/ws/chat` - WebSocket connection for real-time chat

### HTTP
- `GET /` - Chat interface (HTML)
- `GET /health` - Health check endpoint
- `GET /static/{file_path}` - Static files (CSS, JS, images)

**Note:** Backend runs on port **8000**, Frontend runs on port **3000**

### Example Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T20:27:14.254772"
}
```

## ⚙️ Configuration / التكوين

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes |
| `OPENAI_MODEL` | GPT model to use | `gpt-4` | No |
| `OPENAI_MAX_TOKENS` | Maximum tokens | `2000` | No |
| `OPENAI_TEMPERATURE` | Model temperature | `0.7` | No |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `DEBUG` | Debug mode | `True` | No |

<div dir="rtl">

| المتغير | الوصف | القيمة الافتراضية | مطلوب |
|---------|-------|-------------------|-------|
| `OPENAI_API_KEY` | مفتاح OpenAI API | - | نعم |
| `OPENAI_MODEL` | نموذج GPT المستخدم | `gpt-4` | لا |
| `OPENAI_MAX_TOKENS` | الحد الأقصى للتوكنز | `2000` | لا |
| `OPENAI_TEMPERATURE` | درجة الإبداع | `0.7` | لا |
| `HOST` | عنوان الخادم | `0.0.0.0` | لا |
| `PORT` | منفذ الخادم | `8000` | لا |
| `DEBUG` | وضع التطوير | `True` | لا |

</div>

## 🛠️ Development / التطوير

### Running in Development Mode

```bash
# With auto-reload
python run.py

# Or with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Features

1. **Add a new service**: Create a file in `app/services/`
2. **Add a new endpoint**: Modify `app/main.py`
3. **Modify the UI**: Edit `templates/chat.html`
4. **Update configuration**: Modify `app/core/config.py`

<div dir="rtl">

### إضافة ميزات جديدة

1. **إضافة خدمة جديدة**: أنشئ ملف في `app/services/`
2. **إضافة endpoint جديد**: عدّل `app/main.py`
3. **تعديل الواجهة**: عدّل `templates/chat.html`
4. **تحديث التكوين**: عدّل `app/core/config.py`

</div>

## 📦 Dependencies / المتطلبات

### Core Dependencies
- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **OpenAI** - AI integration
- **Pydantic** - Data validation
- **WebSocket** - Real-time communication

### Additional Dependencies (from requirements.txt)
- Social Media APIs (Tweepy, yt-dlp, Instaloader)
- Browser Automation (Playwright, Selenium)
- Media Processing (OpenCV, MoviePy, Pillow)
- AI/ML Libraries (PyTorch, Transformers, LangChain)
- Database Support (PostgreSQL, MongoDB, Redis)
- Task Queue (Celery, Flower)

<div dir="rtl">

### المتطلبات الأساسية
- **FastAPI** - إطار عمل ويب حديث
- **Uvicorn** - خادم ASGI
- **OpenAI** - تكامل الذكاء الاصطناعي
- **Pydantic** - التحقق من البيانات
- **WebSocket** - الاتصال المباشر

</div>

## 🐛 Troubleshooting / حل المشاكل

### Common Issues

1. **UnicodeEncodeError on Windows**
   - The `run.py` script handles encoding automatically
   - Make sure you're using Python 3.11+

2. **ModuleNotFoundError**
   - Activate the virtual environment first
   - Install dependencies: `pip install -r requirements.txt`

3. **OpenAI API Error**
   - Check your API key in `.env` file
   - Ensure you have credits in your OpenAI account

4. **Port already in use**
   - Change the PORT in `.env` file
   - Or kill the process using the port

<div dir="rtl">

### المشاكل الشائعة

1. **خطأ UnicodeEncodeError على Windows**
   - سكربت `run.py` يتعامل مع الترميز تلقائياً
   - تأكد من استخدام Python 3.11+

2. **خطأ ModuleNotFoundError**
   - فعّل البيئة الافتراضية أولاً
   - ثبّت المتطلبات: `pip install -r requirements.txt`

3. **خطأ OpenAI API**
   - تحقق من مفتاح API في ملف `.env`
   - تأكد من وجود رصيد في حساب OpenAI

4. **المنفذ مستخدم بالفعل**
   - غيّر PORT في ملف `.env`
   - أو أوقف العملية التي تستخدم المنفذ

</div>

## 📄 License / الترخيص

This project is licensed under the MIT License - see the LICENSE file for details.

<div dir="rtl">

هذا المشروع مرخص تحت رخصة MIT - راجع ملف LICENSE للتفاصيل.

</div>

## 🤝 Contributing / المساهمة

Contributions are welcome! Please feel free to submit a Pull Request.

<div dir="rtl">

المساهمات مرحب بها! لا تتردد في إرسال Pull Request.

</div>

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 👤 Author / المؤلف

**Mrsos07**
- GitHub: [@Mrsos07](https://github.com/Mrsos07)

## 🔗 Links / الروابط

- Repository: [https://github.com/Mrsos07/Moj-Agentic-AI](https://github.com/Mrsos07/Moj-Agentic-AI)
- OpenAI API: [https://platform.openai.com](https://platform.openai.com)
- FastAPI Docs: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)

## 📝 Changelog / سجل التغييرات

### Version 2.0.0 (Current)
- ✅ Complete rewrite with FastAPI
- ✅ React Frontend with Vite + TailwindCSS
- ✅ Arabic RTL interface
- ✅ WebSocket real-time communication
- ✅ OpenAI GPT-4 integration
- ✅ Modern component-based architecture
- ✅ Axios for API calls
- ✅ React Icons integration
- ✅ Comprehensive requirements.txt
- ✅ Windows encoding fixes

<div dir="rtl">

### الإصدار 2.0.0 (الحالي)
- ✅ إعادة كتابة كاملة مع FastAPI
- ✅ واجهة أمامية React مع Vite + TailwindCSS
- ✅ واجهة عربية RTL
- ✅ اتصال WebSocket مباشر
- ✅ تكامل OpenAI GPT-4
- ✅ بنية معمارية حديثة قائمة على المكونات
- ✅ Axios للاتصال بالـ API
- ✅ تكامل React Icons
- ✅ requirements.txt شامل
- ✅ إصلاحات ترميز Windows

</div>

---

<div dir="rtl">

**صنع بـ ❤️ باستخدام Python و FastAPI**

</div>

**Made with ❤️ using Python and FastAPI**
