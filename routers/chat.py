import uuid
import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from services.templates import render
from services.auth_service import require_session
from services import groq_agent

router = APIRouter()


@router.get("/chat")
async def chat_page(request: Request):
    user = require_session(request)
    session_id = str(uuid.uuid4())
    return render(request, "chat.html", {"user": user, "session_id": session_id})


@router.websocket("/chat/ws")
async def chat_ws(websocket: WebSocket, session_id: str, user_id: str, role: str):
    await websocket.accept()
    mcp_tools = getattr(websocket.app.state, "mcp_tools", [])

    async def send_json(payload: dict):
        await websocket.send_text(json.dumps(payload))

    async def send_token(text: str):
        await websocket.send_text(text)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            message = data.get("message", "")
            lat = data.get("lat")
            lng = data.get("lng")
            if not message:
                continue

            groq_agent.init_session(session_id, role, user_id, lat, lng)

            try:
                await groq_agent.run_agent_turn(session_id, message, mcp_tools, send_json, send_token)
            except Exception as e:
                await send_json({"type": "error", "message": str(e)})
                await send_json({"type": "done"})

    except WebSocketDisconnect:
        pass
