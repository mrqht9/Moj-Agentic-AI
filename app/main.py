# تحميل .env الرئيسي إلى متغيرات البيئة (يخدم جميع الخدمات الفرعية)
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import json
from datetime import datetime
from typing import List
import asyncio
import uuid
from io import BytesIO

try:
    from PIL import Image
except Exception:
    Image = None

from app.services.ai_service import AIService, ai_service
from app.services.webhook_service import WebhookService
from app.core.config import settings
from app.db.database import init_db, get_db
from app.auth.routes import router as auth_router
from app.api.intent_routes import router as intent_router
from app.api.admin_routes import router as admin_router
from app.api.agent_routes import router as agent_router
from app.api.conversation_routes import router as conversation_router
from app.api.x_routes import router as x_router
from app.api.admin_accounts_routes import router as admin_accounts_router
from app.api.user_accounts_routes import router as user_accounts_router
from app.api.schedule_routes import router as schedule_router
from app.api.telegram_routes import router as telegram_router
from app.api.trend_routes import router as trend_router
from app.agents.agent_manager import agent_manager
from app.services import x_bridge
from app.services.memory_service import memory_service
from app.trend_detector.scheduler.scheduler import trend_scheduler
from app.scheduler.tick import scheduler_tick

app = FastAPI(title="كنق الاتمته - Chatbot API", version="1.0.0")

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized")
    
    try:
        agent_manager.initialize()
        print("AI Agents initialized successfully")
    except Exception as e:
        print(f"Warning: AI Agents initialization failed: {str(e)}")
        print("Check .env.agents file for LLM configuration")

    try:
        trend_scheduler.start()
        print("Trend Detector scheduler started")
    except Exception as e:
        print(f"Warning: Trend Detector scheduler failed: {str(e)}")

    try:
        x_bridge.start_xsuite_server()
    except Exception as e:
        print(f"Warning: X Suite server failed to start: {str(e)}")

    try:
        x_bridge.start_loginx_server()
    except Exception as e:
        print(f"Warning: LoginX server failed to start: {str(e)}")

    try:
        from app.services import identity_bridge
        identity_bridge.start_identity_server()
    except Exception as e:
        print(f"Warning: Identity server failed to start: {str(e)}")

    try:
        asyncio.create_task(scheduler_tick())
        print("Scheduler tick started (every 30s)")
    except Exception as e:
        print(f"Warning: Scheduler tick failed: {str(e)}")

# Include auth routes
app.include_router(auth_router)

# Include intent recognition routes
app.include_router(intent_router)

# Include admin routes
app.include_router(admin_router)

# Include agent routes
app.include_router(agent_router)

# Include conversation routes
app.include_router(conversation_router)

# Include X platform routes
app.include_router(x_router)

# Include accounts management routes
app.include_router(admin_accounts_router)
app.include_router(user_accounts_router)

# Include trend detector routes
app.include_router(trend_router)

# Include schedule event routes
app.include_router(schedule_router)

# Include telegram integration routes
app.include_router(telegram_router)

# CORS Configuration - تقييد النطاقات المسموحة
import os
default_allowed_origins = ",".join([
    "http://localhost:3000",
    "http://localhost:5173",
    "https://stopping-idly-endearing.ngrok-free.dev",
])
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", default_allowed_origins).split(",")
    if origin.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", r"https://.*\.ngrok-free\.dev").strip() or None

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

uploads_path = static_path / "uploads"
uploads_path.mkdir(parents=True, exist_ok=True)

# ─── واجهة React المبنية (frontend/dist) ───
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="react_assets",
    )

ai_service = AIService()
webhook_service = WebhookService()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # mapping من user_id إلى قائمة WebSockets للإشعارات (تسجيل دخول، إلخ)
        self.user_websockets: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # إزالة من mapping المستخدمين
        for uid in list(self.user_websockets.keys()):
            if websocket in self.user_websockets[uid]:
                self.user_websockets[uid].remove(websocket)
                if not self.user_websockets[uid]:
                    del self.user_websockets[uid]

    def register_user(self, user_id, websocket: WebSocket):
        """ربط user_id بـ WebSocket لإرسال إشعارات لاحقة."""
        if user_id is None:
            return
        try:
            uid = int(user_id)
        except (ValueError, TypeError):
            return
        self.user_websockets.setdefault(uid, [])
        if websocket not in self.user_websockets[uid]:
            self.user_websockets[uid].append(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def send_to_user(self, user_id, message: dict) -> int:
        """يرسل رسالة لكل WebSockets الخاصة بمستخدم. يرجع عدد الرسائل المرسلة."""
        if user_id is None:
            return 0
        try:
            uid = int(user_id)
        except (ValueError, TypeError):
            return 0
        sent = 0
        for ws in list(self.user_websockets.get(uid, [])):
            try:
                await ws.send_json(message)
                sent += 1
            except Exception:
                # WebSocket مقطوع — نشيله
                try:
                    self.user_websockets[uid].remove(ws)
                except Exception:
                    pass
        return sent

manager = ConnectionManager()

# Models for API requests
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/", response_class=HTMLResponse)
async def get_react_app():
    """يخدّم تطبيق React المبني — هو الواجهة الرئيسية للنظام."""
    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(react_index)
    # احتياطي: لو React لم يُبنَ بعد، نخدّم الواجهة القديمة كـ fallback
    legacy_html = Path(__file__).parent.parent / "templates" / "chat.html"
    if legacy_html.exists():
        return FileResponse(legacy_html)
    return HTMLResponse(
        content=(
            "<h1>تطبيق React غير مبني</h1>"
            "<p>شغّل: <code>cd frontend && npm install && npm run build</code></p>"
        ),
        status_code=503,
    )

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("message", "")
            session_id = message_data.get("session_id", None)
            user_id = message_data.get("user_id", None)
            user_email = message_data.get("user_email", None)
            attachment = message_data.get("attachment", None)
            file_upload = message_data.get("file_upload", None)

            # ربط هذا الـ WebSocket بـ user_id لإرسال إشعارات تسجيل الدخول لاحقاً
            if user_id:
                manager.register_user(user_id, websocket)

            await manager.send_message({
                "type": "user_message",
                "message": user_message,
                "attachment": attachment,
                "timestamp": datetime.now().isoformat()
            }, websocket)
            
            await manager.send_message({
                "type": "typing",
                "status": True
            }, websocket)
            
            try:
                # معالجة ملفات الكوكيز و CSV
                if file_upload:
                    file_name = file_upload.get("name", "")
                    file_content = file_upload.get("content", "")
                    file_type = file_upload.get("type", "")
                    
                    # ── ملف CSV لتسجيل دخول جماعي ──
                    if file_name.endswith('.csv'):
                        try:
                            import csv, io, threading
                            from app.agents.tools import x_login_account, LOGINX_BASE_URL, LOGINX_API_KEY
                            
                            reader = csv.DictReader(io.StringIO(file_content))
                            accounts = []
                            for row in reader:
                                username = (row.get("username") or "").strip()
                                password = (row.get("password") or "").strip()
                                email = (row.get("email") or "").strip()
                                if username and password:
                                    accounts.append({"username": username, "password": password, "email": email})
                            
                            if not accounts:
                                await manager.send_message({
                                    "type": "assistant_message",
                                    "message": "❌ ملف CSV فارغ أو لا يحتوي على أعمدة username و password",
                                    "timestamp": datetime.now().isoformat()
                                }, websocket)
                                continue
                            
                            await manager.send_message({
                                "type": "typing",
                                "status": False
                            }, websocket)
                            
                            await manager.send_message({
                                "type": "assistant_message",
                                "message": f"📋 تم قراءة **{len(accounts)}** حساب من ملف CSV\n\n🔄 جاري بدء تسجيل الدخول الجماعي...\n\n⏳ سيتم تسجيل كل حساب على حدة. هذه العملية قد تستغرق وقتاً.",
                                "timestamp": datetime.now().isoformat()
                            }, websocket)
                            
                            # تسجيل دخول جماعي عبر API
                            import requests
                            headers = {"X-API-Key": LOGINX_API_KEY, "Content-Type": "application/json"}
                            try:
                                resp = requests.post(
                                    f"{LOGINX_BASE_URL}/api/login/bulk",
                                    json={"accounts": accounts},
                                    headers=headers, timeout=10
                                )
                                data = resp.json()
                                if data.get("success"):
                                    session_id = data.get("session_id")
                                    await manager.send_message({
                                        "type": "assistant_message",
                                        "message": f"✅ بدأت عملية تسجيل الدخول الجماعي\n\n📊 عدد الحسابات: {len(accounts)}\n🔑 Session ID: `{session_id}`\n\nسيتم إعلامك عند الانتهاء.",
                                        "timestamp": datetime.now().isoformat()
                                    }, websocket)
                                else:
                                    await manager.send_message({
                                        "type": "assistant_message",
                                        "message": f"❌ فشل بدء التسجيل الجماعي: {data.get('error', 'خطأ')}",
                                        "timestamp": datetime.now().isoformat()
                                    }, websocket)
                            except requests.ConnectionError:
                                await manager.send_message({
                                    "type": "assistant_message",
                                    "message": "❌ سيرفر LoginX غير متصل!\n\nتأكد من تشغيل سيرفر loginx على بورت 5000",
                                    "timestamp": datetime.now().isoformat()
                                }, websocket)
                        except Exception as e:
                            await manager.send_message({
                                "type": "typing",
                                "status": False
                            }, websocket)
                            await manager.send_message({
                                "type": "assistant_message",
                                "message": f"❌ خطأ في معالجة ملف CSV: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            }, websocket)
                        continue
                    
                    # ── ملف JSON كوكيز ──
                    elif file_name.endswith('.json') and 'auth_token' in file_content:
                        # معالجة ملف كوكيز X مباشرة
                        try:
                            from app.agents.tools import _x_save_cookies_sync
                            cookies_data = json.loads(file_content)
                            label = file_name.replace('.json', '').strip()
                            
                            result = _x_save_cookies_sync(cookies_data, label) or {}
                            
                            await manager.send_message({
                                "type": "typing",
                                "status": False
                            }, websocket)
                            
                            if result and result.get("success"):
                                await manager.send_message({
                                    "type": "assistant_message",
                                    "message": f"✅ {result.get('message', 'تم حفظ الكوكيز بنجاح')}",
                                    "timestamp": datetime.now().isoformat()
                                }, websocket)
                            else:
                                await manager.send_message({
                                    "type": "assistant_message",
                                    "message": f"❌ {result.get('message', 'فشل حفظ الكوكيز')}",
                                    "timestamp": datetime.now().isoformat()
                                }, websocket)
                        except Exception as e:
                            await manager.send_message({
                                "type": "typing",
                                "status": False
                            }, websocket)
                            await manager.send_message({
                                "type": "assistant_message",
                                "message": f"❌ خطأ في معالجة ملف الكوكيز: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            }, websocket)
                        continue
                    else:
                        await manager.send_message({
                            "type": "assistant_message",
                            "message": "تم استلام الملف. الأنواع المدعومة:\n\n📄 **CSV** — تسجيل دخول جماعي (أعمدة: username, password, email)\n📎 **JSON** — ملف كوكيز X (يحتوي على auth_token)",
                            "timestamp": datetime.now().isoformat()
                        }, websocket)
                        continue

                if (not user_message or not str(user_message).strip()) and attachment:
                    try:
                        db = next(get_db())
                        conversation = memory_service.get_or_create_conversation(
                            db=db,
                            user_id=user_id,
                            session_id=session_id
                        )
                        memory_service.add_message(
                            db=db,
                            conversation_id=conversation.id,
                            role="user",
                            content="",
                            metadata={"attachment": attachment}
                        )
                    except Exception as e:
                        print(f"Warning: Failed to persist attachment-only message: {str(e)}")

                    await manager.send_message({
                        "type": "typing",
                        "status": False
                    }, websocket)
                    await manager.send_message({
                        "type": "assistant_message",
                        "message": "تم استلام المرفق. أرسل نصًا مع المرفق إذا كنت تريد مني معالجته.",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                    continue

                # الحصول على جلسة قاعدة البيانات
                db = next(get_db())
                
                # استخدام نظام الوكلاء الذكية مع الذاكرة
                agent_result = agent_manager.process_user_message(
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={"attachment": attachment} if attachment else None,
                    db=db
                )
                
                await manager.send_message({
                    "type": "typing",
                    "status": False
                }, websocket)
                
                # إرسال رد الوكيل
                if not agent_result or not isinstance(agent_result, dict):
                    agent_result = {"success": False, "message": None}
                
                response_message = agent_result.get("message")
                
                if agent_result.get("success") and response_message:
                    # إضافة معلومات إضافية إذا كانت متاحة
                    metadata = {}
                    if agent_result.get("intent_result"):
                        metadata["intent"] = agent_result["intent_result"].get("intent")
                        metadata["confidence"] = agent_result["intent_result"].get("confidence")
                    if agent_result.get("agent"):
                        metadata["agent"] = agent_result["agent"]
                    
                    await manager.send_message({
                        "type": "assistant_message",
                        "message": response_message,
                        "metadata": metadata,
                        "attachment": attachment,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                elif response_message:
                    # في حالة الفشل مع وجود رسالة
                    await manager.send_message({
                        "type": "assistant_message",
                        "message": response_message,
                        "attachment": attachment,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                else:
                    # الوكيل ما لقى نية مطابقة → النظام بوت خدمات، مو شات عام
                    out_of_scope_message = (
                        "🤖 أنا **موج**، بوت متخصص لإدارة حساباتك على منصات التواصل — لست شاتاً عاماً.\n\n"
                        "🎯 **خدماتي الرئيسية:**\n"
                        "• 📝 نشر التغريدات\n"
                        "• ❤️ التفاعل (لايك، إعادة نشر، رد، بوكمارك)\n"
                        "• 📊 متابعة الترندات وتحليلها\n"
                        "• 🆔 توليد هويات وهمية بالصور\n"
                        "• 👤 إدارة الحسابات (إضافة، حذف، عرض)\n"
                        "• ⏰ جدولة المنشورات\n"
                        "• 🎨 تحديث البروفايل\n\n"
                        "💡 اكتب **مساعدة** لعرض كل الأوامر بأمثلة."
                    )

                    conversation_id = agent_result.get("conversation_id")
                    if db and conversation_id:
                        try:
                            memory_service.add_message(
                                db=db,
                                conversation_id=conversation_id,
                                role="assistant",
                                content=out_of_scope_message,
                                agent="Scope_Guard",
                            )
                        except Exception as e:
                            print(f"[ScopeGuard] Failed to persist message: {str(e)[:200]}")

                    await manager.send_message({
                        "type": "assistant_message",
                        "message": out_of_scope_message,
                        "metadata": {"agent": "Scope_Guard"},
                        "attachment": attachment,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                    
            except Exception as e:
                await manager.send_message({
                    "type": "typing",
                    "status": False
                }, websocket)
                await manager.send_message({
                    "type": "error",
                    "message": f"حدث خطأ: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/uploads")
async def upload_file(file: UploadFile = File(...)):
    max_size_bytes = 10 * 1024 * 1024
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()

    allowed_images = {".png", ".jpg", ".jpeg", ".webp"}
    allowed_docs = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}
    allowed_data = {".csv", ".json", ".txt"}
    allowed = allowed_images | allowed_docs | allowed_data
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="نوع الملف غير مسموح")

    data = await file.read()
    if len(data) > max_size_bytes:
        raise HTTPException(status_code=400, detail="حجم الملف كبير جدًا")

    kind = "image" if ext in allowed_images else "document"

    if kind == "image":
        if Image is not None:
            try:
                Image.open(BytesIO(data)).verify()
            except Exception:
                raise HTTPException(status_code=400, detail="ملف الصورة غير صالح")
        else:
            is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
            is_jpg = data.startswith(b"\xff\xd8\xff")
            is_webp = len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP"
            if not (is_png or is_jpg or is_webp):
                raise HTTPException(status_code=400, detail="ملف الصورة غير صالح")
    else:
        if ext == ".pdf" and not data.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="ملف PDF غير صالح")
        if ext in {".docx", ".xlsx"} and not data.startswith(b"PK"):
            raise HTTPException(status_code=400, detail="ملف غير صالح")

    safe_name = f"{uuid.uuid4().hex}{ext}"
    out_path = uploads_path / safe_name
    out_path.write_bytes(data)

    return {
        "url": f"/static/uploads/{safe_name}",
        "original_name": filename,
        "content_type": file.content_type,
        "size": len(data),
        "kind": kind
    }

@app.post("/api/send-message")
async def send_message_to_n8n(request: MessageRequest):
    """
    Endpoint POST لإرسال رسالة إلى n8n webhook واستقبال الرد
    
    يمكن استخدام هذا الـ endpoint لإرسال رسائل مباشرة إلى n8n والحصول على الرد
    """
    try:
        n8n_response = await webhook_service.send_message_to_n8n(
            user_message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        if n8n_response:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "تم إرسال الرسالة إلى n8n بنجاح",
                    "response": n8n_response,
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "فشل الحصول على رد من n8n. يرجى التحقق من أن n8n webhook يعمل بشكل صحيح.",
                    "timestamp": datetime.now().isoformat()
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"حدث خطأ أثناء إرسال الرسالة: {str(e)}"
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ────────────────────────────────────────────────────────────────────────────
# Callback داخلي يستدعيه سيرفر loginx عند اكتمال تسجيل دخول حساب X.
# يرسل إشعار في الشات للمستخدم عبر WebSocket.
# ليس مكشوفًا للعموم — يقبل اتصال محلي فقط (127.0.0.1).
# ────────────────────────────────────────────────────────────────────────────
@app.post("/api/internal/login-callback", include_in_schema=False)
async def login_callback(payload: Dict[str, Any], request):
    # حماية: يقبل فقط من localhost (loginx يشتغل محلياً)
    client_host = (request.client.host if request.client else "") if hasattr(request, "client") else ""
    if client_host not in ("127.0.0.1", "localhost", "::1", ""):
        raise HTTPException(status_code=403, detail="callback مسموح محلياً فقط")

    user_id = payload.get("user_id")
    if not user_id:
        return {"ok": True, "note": "no user_id, nothing to notify"}

    account = payload.get("account") or payload.get("username") or "حساب"
    success = bool(payload.get("success"))
    finalized = bool(payload.get("finalized"))
    error = payload.get("error", "")

    if success and finalized:
        msg = (
            f"✅ **تم تسجيل دخول الحساب '{account}' بنجاح!**\n\n"
            f"🎉 الحساب أصبح متاحاً للنشر والتفاعل.\n"
            f"💡 جرّب: `الحساب {account} انشر [النص]`"
        )
    elif success and not finalized:
        msg = (
            f"⚠️ **تسجيل دخول '{account}' اكتمل لكن فيه مشكلة في حفظ الكوكيز.**\n\n"
            f"حاول مرة ثانية أو ارفع ملف الكوكيز يدوياً."
        )
    else:
        msg = (
            f"❌ **فشل تسجيل دخول الحساب '{account}'**\n\n"
            + (f"📋 السبب: {error}\n\n" if error else "")
            + "💡 تأكد من اسم المستخدم وكلمة المرور وأعد المحاولة."
        )

    sent = await manager.send_to_user(user_id, {
        "type": "assistant_message",
        "message": msg,
        "metadata": {"agent": "X_Login_Notification"},
        "timestamp": datetime.now().isoformat(),
    })

    return {"ok": True, "notified": sent}


# ════════════════════════════════════════════════════════════════════════════
# Catch-all لدعم React Router (يجب أن يبقى آخر route — لا تضف شيئاً بعده!)
# يلتقط أي مسار غير معروف ويخدّم index.html لتتولاه React.
# ════════════════════════════════════════════════════════════════════════════
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_react_spa(full_path: str):
    # لا نلتقط مسارات الـ API أو WebSocket (هذي مسجلة قبل، الـ catch-all
    # يلتقط فقط ما لم يُطابق قبله، لكن نضيف حماية إضافية).
    if full_path.startswith(("api/", "ws/", "static/", "assets/")):
        raise HTTPException(status_code=404)

    if not FRONTEND_DIST.exists():
        raise HTTPException(status_code=404, detail="React build not found")

    # لو الملف موجود فعلياً في dist (favicon, robots.txt, ...) → نخدمه مباشرة
    file_path = FRONTEND_DIST / full_path
    if file_path.is_file():
        return FileResponse(file_path)

    # خلاف ذلك → نرجع index.html و React Router يتولى التوجيه
    return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
