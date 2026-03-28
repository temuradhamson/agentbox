"""Shared Agent Box token management."""
import os

import httpx

from app.core.config import settings
from app.core.security import get_agent_box_token, set_agent_box_token


async def ensure_ab_token() -> str:
    token = get_agent_box_token()
    if token:
        return token
    login = os.getenv("AB_LOGIN", "admin")
    password = os.getenv("AB_PASSWORD", "admin123")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{settings.AGENT_BOX_URL}/auth/login",
            json={"login": login, "password": password},
        )
        if r.status_code == 200:
            t = r.json().get("token", "")
            set_agent_box_token(t)
            return t
    raise RuntimeError("Cannot authenticate with Agent Box")
