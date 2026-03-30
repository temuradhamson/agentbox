import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/api/asr", tags=["asr"], dependencies=[Depends(get_current_user)])


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()

    async with httpx.AsyncClient(timeout=600.0, verify=False) as client:
        resp = await client.post(
            settings.ASR_API_URL,
            files={"file": (audio.filename or "audio.wav", audio_bytes, audio.content_type or "audio/wav")},
            data={
                "language": settings.ASR_LANGUAGE,
                "with_normalize": "true" if settings.ASR_NORMALIZE else "false",
                "token": settings.ASR_TOKEN,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ASR error: {resp.text}")

    return resp.json()
