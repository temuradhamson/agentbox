import asyncio

import websockets
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import verify_token

router = APIRouter()


@router.websocket("/ws/chat/{session_id}")
async def ws_chat_proxy(ws: WebSocket, session_id: str, token: str = Query("")):
    payload = verify_token(token)
    if not payload:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()

    upstream_url = f"{settings.CHATCAP_URL.replace('http', 'ws')}/ws/chat/{session_id}"
    try:
        async with websockets.connect(upstream_url) as upstream:

            async def client_to_upstream():
                try:
                    while True:
                        data = await ws.receive_text()
                        await upstream.send(data)
                except WebSocketDisconnect:
                    pass

            async def upstream_to_client():
                try:
                    async for msg in upstream:
                        await ws.send_text(msg)
                except websockets.ConnectionClosed:
                    pass

            await asyncio.gather(client_to_upstream(), upstream_to_client())
    except Exception:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
