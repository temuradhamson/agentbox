import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.core.agentbox import ensure_ab_token
from app.core.config import settings

router = APIRouter(prefix="/api/asr", tags=["asr"], dependencies=[Depends(get_current_user)])


@router.post("/transcribe")
async def transcribe(audio: UploadFile):
    try:
        token = await ensure_ab_token()
    except Exception:
        raise HTTPException(502, "Agent Box auth failed")

    content = await audio.read()
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{settings.AGENT_BOX_URL}/asr",
                headers={"Authorization": f"Bearer {token}"},
                files={"audio": (audio.filename or "recording.wav", content, audio.content_type or "audio/wav")},
                timeout=None,  # no limit
            )
        except httpx.ConnectError:
            raise HTTPException(502, "Agent Box unavailable")

    if r.status_code != 200:
        raise HTTPException(r.status_code, "ASR error")
    return r.json()
