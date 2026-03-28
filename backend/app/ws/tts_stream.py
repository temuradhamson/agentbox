import asyncio

import websockets
from fastapi import APIRouter, Query, WebSocket

from app.core.agentbox import ensure_ab_token
from app.core.config import settings
from app.core.security import verify_token

router = APIRouter()


@router.websocket("/ws/tts")
async def ws_tts_proxy(ws: WebSocket, token: str = Query("")):
    payload = verify_token(token)
    if not payload:
        await ws.close(code=4001, reason="Unauthorized")
        return

    try:
        ab_token = await ensure_ab_token()
    except Exception:
        await ws.close(code=4002, reason="Agent Box auth failed")
        return

    await ws.accept()

    upstream_url = f"{settings.AGENT_BOX_URL.replace('http', 'ws')}/ws/tts?token={ab_token}"
    try:
        async with websockets.connect(upstream_url) as upstream:

            async def keepalive():
                try:
                    while True:
                        await asyncio.sleep(25)
                        await ws.send_text('{"ping":true}')
                except Exception:
                    pass

            async def upstream_to_client():
                try:
                    async for msg in upstream:
                        if isinstance(msg, bytes):
                            await ws.send_bytes(msg)
                        else:
                            await ws.send_text(msg)
                except websockets.ConnectionClosed:
                    pass

            await asyncio.gather(keepalive(), upstream_to_client())
    except Exception:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
