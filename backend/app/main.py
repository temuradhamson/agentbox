from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, asr, health, sessions
from app.core.config import settings
from app.ws import terminal_proxy, tts_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check connectivity on startup
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in [("Agent Box", settings.AGENT_BOX_URL)]:
            try:
                await client.get(url)
                print(f"  {name} ({url}): reachable")
            except Exception:
                print(f"  {name} ({url}): offline (will retry on request)")
    yield


app = FastAPI(title="Agent Hub", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3005", "http://127.0.0.1:3005", "http://localhost:3003", "http://127.0.0.1:3003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(asr.router)

# WebSocket routes
app.include_router(terminal_proxy.router)
app.include_router(tts_stream.router)
