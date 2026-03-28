from fastapi import Cookie, Depends, Header, HTTPException, status

from app.core.security import verify_token


async def get_current_user(
    authorization: str | None = Header(None),
    session_token: str | None = Cookie(None),
) -> dict:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif session_token:
        token = session_token

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return payload
