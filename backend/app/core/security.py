from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

_agent_box_token: str | None = None


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def get_agent_box_token() -> str | None:
    return _agent_box_token


def set_agent_box_token(token: str) -> None:
    global _agent_box_token
    _agent_box_token = token
