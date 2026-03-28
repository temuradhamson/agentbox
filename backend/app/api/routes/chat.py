import httpx
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/api/sessions", tags=["chat"], dependencies=[Depends(get_current_user)])


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    """Fetch structured messages from ChatCap REST API."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{settings.CHATCAP_URL}/api/sessions/{session_id}/messages")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"messages": []}
