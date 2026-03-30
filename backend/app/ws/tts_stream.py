import asyncio

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.security import verify_token
from app.core.tts import broadcast_tts_url, extract_tts_url, tts_clients

router = APIRouter()


# ── HTTP endpoints ──

class TTSSpeakRequest(BaseModel):
    url: str


@router.post("/api/tts/hook")
async def tts_hook(request: Request):
    """Receive raw PostToolUse hook JSON from Claude Code."""
    try:
        data = await request.json()
        url = extract_tts_url(data)
        if url:
            await broadcast_tts_url(url)
    except Exception:
        pass
    return {"ok": True}


@router.post("/api/tts/speak")
async def tts_speak(payload: TTSSpeakRequest):
    await broadcast_tts_url(payload.url)
    return {"ok": True, "delivered": len(tts_clients)}


# ── WebSocket endpoint ──

@router.websocket("/ws/tts")
async def ws_tts(ws: WebSocket, token: str = Query("")):
    payload = verify_token(token)
    if not payload:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    tts_clients.add(ws)

    async def keepalive():
        try:
            while True:
                await asyncio.sleep(25)
                await ws.send_text('{"ping":true}')
        except Exception:
            pass

    try:
        ka_task = asyncio.create_task(keepalive())
        while True:
            await ws.receive_text()  # keep-alive reads
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        ka_task.cancel()
        tts_clients.discard(ws)
