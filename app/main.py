from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
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
from pathlib import Path

from app.services.ai_service import AIService
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
from app.agents.agent_manager import agent_manager
from app.services import x_bridge
from app.api.trend_routes import router as trend_router
from app.api.schedule_routes import router as schedule_router
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
    
    # Start Trend Detector scheduler
    try:
        trend_scheduler.start()
        print("Trend Detector scheduler started")
    except Exception as e:
        print(f"Warning: Trend Detector scheduler failed: {str(e)}")
    
    # Start app/x (X Suite) server in background
    try:
        x_bridge.start_xsuite_server()
    except Exception as e:
        print(f"Warning: X Suite server failed to start: {str(e)}")

    # Start scheduler tick
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

# CORS Configuration - تقييد النطاقات المسموحة
import os
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=3600,
)

static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

ai_service = AIService()
webhook_service = WebhookService()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

# Models for API requests
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    html_file = Path(__file__).parent.parent / "templates" / "chat.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(content="<h1>Chat interface not found</h1>", status_code=404)

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
            print(f"[WS] رسالة واردة: '{user_message[:80]}'", flush=True)
            
            await manager.send_message({
                "type": "user_message",
                "message": user_message,
                "timestamp": datetime.now().isoformat()
            }, websocket)
            
            await manager.send_message({
                "type": "typing",
                "status": True
            }, websocket)
            
            try:
                # الحصول على جلسة قاعدة البيانات
                db = next(get_db())
                
                print(f"[WS] Processing message: '{user_message[:80]}' user_id={user_id}", flush=True)
                agent_result = agent_manager.process_user_message(
                    message=user_message,
                    user_id=user_id,
                    session_id=session_id,
                    db=db
                )
                print(f"[WS] agent_result: success={agent_result.get('success') if agent_result else 'None'}, agent={agent_result.get('agent') if agent_result else 'None'}", flush=True)
                
                await manager.send_message({
                    "type": "typing",
                    "status": False
                }, websocket)
                
                # إرسال رد الوكيل
                if agent_result and agent_result.get("success"):
                    response_message = agent_result.get("message", "")
                    
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
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                elif agent_result and agent_result.get("message"):
                    await manager.send_message({
                        "type": "assistant_message",
                        "message": agent_result.get("message"),
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                else:
                    # Fallback — try AI service, or give helpful static response
                    fallback = None
                    print(f"[WS] FALLBACK to AI service (agent returned None or no success)", flush=True)
                    try:
                        fallback = await ai_service.get_response(user_message)
                    except Exception:
                        pass
                    
                    if not fallback or "مفتاح الذكاء الاصطناعي" in fallback:
                        fallback = (
                            "هلا! 👋 حالياً أقدر أساعدك في:\n\n"
                            "📊 **تحليل الترندات:**\n"
                            "• \"وش الترندات؟\" — نظرة عامة\n"
                            "• \"ترندات حارة\" — الأكثر رواجاً\n"
                            "• \"ترند السعودية\" — بحث محدد\n\n"
                            "📱 **إدارة الحسابات:**\n"
                            "• \"أضف حساب تويتر\"\n"
                            "• \"عرض حساباتي\"\n\n"
                            "💡 جرب تسألني عن الترندات!"
                        )
                    
                    await manager.send_message({
                        "type": "assistant_message",
                        "message": fallback,
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

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
