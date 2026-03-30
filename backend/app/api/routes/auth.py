from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    if body.login != settings.AUTH_LOGIN or body.password != settings.AUTH_PASSWORD:
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": body.login})
    response.set_cookie("session_token", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    return {"token": token, "user": body.login}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}
