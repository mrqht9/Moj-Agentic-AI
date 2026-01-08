from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from datetime import datetime
from typing import List
import asyncio
from pathlib import Path

from app.services.ai_service import AIService
from app.core.config import settings

app = FastAPI(title="كنق الاتمته - Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

ai_service = AIService()

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
                ai_response = await ai_service.get_response(user_message)
                
                await manager.send_message({
                    "type": "typing",
                    "status": False
                }, websocket)
                
                await manager.send_message({
                    "type": "assistant_message",
                    "message": ai_response,
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
