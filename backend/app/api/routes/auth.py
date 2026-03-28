import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, set_agent_box_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{settings.AGENT_BOX_URL}/auth/login",
                json={"login": body.login, "password": body.password},
                timeout=10,
            )
        except httpx.ConnectError:
            raise HTTPException(502, "Agent Box unavailable")

    if r.status_code != 200:
        raise HTTPException(401, "Invalid credentials")

    data = r.json()
    set_agent_box_token(data["token"])

    token = create_access_token({"sub": body.login})
    response.set_cookie("session_token", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    return {"token": token, "user": body.login}


@router.get("/agent-box-token")
async def get_ab_token(user: dict = Depends(get_current_user)):
    """Return Agent Box token for direct WebSocket connections."""
    from app.core.agentbox import ensure_ab_token
    try:
        token = await ensure_ab_token()
        return {"token": token, "url": settings.AGENT_BOX_URL}
    except Exception:
        raise HTTPException(502, "Agent Box unavailable")


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}
