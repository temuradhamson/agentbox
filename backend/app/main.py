from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, asr, health, sessions
from app.ws import terminal_proxy, tts_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Agent Hub", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3005", "http://127.0.0.1:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(asr.router)

# WebSocket + TTS HTTP routes
app.include_router(terminal_proxy.router)
app.include_router(tts_stream.router)

# Serve Nuxt SPA in production (when built frontend exists)
_frontend_dist = Path("/app/frontend/.output/public")
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="spa")
