from fastapi import APIRouter

from app.core.tmux import list_sessions

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    sessions = list_sessions()
    return {"ok": True, "sessions": sessions}
