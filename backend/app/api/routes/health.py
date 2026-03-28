import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    status = {"agent_hub": "ok", "agent_box": "unknown"}

    async with httpx.AsyncClient(timeout=3) as client:
        try:
            r = await client.get(f"{settings.AGENT_BOX_URL}/health")
            status["agent_box"] = "ok" if r.status_code == 200 else "error"
        except Exception:
            status["agent_box"] = "offline"

    return status
