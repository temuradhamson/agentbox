from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import get_agent_box_token, set_agent_box_token

router = APIRouter(prefix="/api/sessions", tags=["sessions"], dependencies=[Depends(get_current_user)])

# In-memory tracking
_activity: dict[str, str | None] = {}  # session_id -> last activity ISO
_msg_counts: dict[str, int] = {}       # session_id -> last known message count
_msg_timestamps: dict[str, dict[int, str]] = {}  # session_id -> {msg_index: ISO timestamp}


def _touch(session_id: str):
    _activity[session_id] = datetime.now(timezone.utc).isoformat()


async def _ensure_ab_token():
    token = get_agent_box_token()
    if token:
        return token
    import os
    login = os.getenv("AB_LOGIN", "admin")
    password = os.getenv("AB_PASSWORD", "admin123")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(
                f"{settings.AGENT_BOX_URL}/auth/login",
                json={"login": login, "password": password},
            )
            if r.status_code == 200:
                t = r.json().get("token", "")
                set_agent_box_token(t)
                return t
        except Exception:
            pass
    raise HTTPException(502, "Cannot authenticate with Agent Box")


async def _headers():
    token = await _ensure_ab_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@router.get("")
async def list_sessions():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{settings.AGENT_BOX_URL}/health", headers=await _headers(), timeout=10)
        except httpx.ConnectError:
            raise HTTPException(502, "Agent Box unavailable")
    if r.status_code != 200:
        raise HTTPException(r.status_code, "Agent Box error")
    data = r.json()
    headers = await _headers()
    sessions_list = []
    for sid in data.get("sessions", []):
        if sid not in _activity:
            _activity[sid] = None
        sessions_list.append({"id": sid, "last_active": _activity[sid] or ""})
    sessions_list.sort(key=lambda s: s["last_active"] or "", reverse=True)
    return {"sessions": sessions_list}


class CreateSession(BaseModel):
    session_id: str
    workdir: str = "/workspace"
    cli: str = "claude"


@router.post("")
async def create_session(body: CreateSession):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.AGENT_BOX_URL}/sessions",
            headers=await _headers(),
            json=body.model_dump(),
            timeout=30,
        )
    _touch(body.session_id)
    return r.json()


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{settings.AGENT_BOX_URL}/sessions/{session_id}/tail",
                headers=await _headers(),
                params={"lines": 500},
            )
            if r.status_code == 200:
                data = r.json()
                output = data.get("text", "") or data.get("output", "")
                if output:
                    from app.core.parser import parse_terminal_output
                    msgs = parse_terminal_output(output)

                    # Track new messages and assign real timestamps
                    now = datetime.now(timezone.utc).isoformat()
                    prev_count = _msg_counts.get(session_id, 0)
                    cur_count = len(msgs)

                    if session_id not in _msg_timestamps:
                        _msg_timestamps[session_id] = {}

                    if cur_count > prev_count:
                        # New messages appeared — stamp them with current time
                        for idx in range(prev_count, cur_count):
                            _msg_timestamps[session_id][idx] = now
                        _msg_counts[session_id] = cur_count
                        _activity[session_id] = now

                    # Apply stored timestamps to messages
                    ts_map = _msg_timestamps.get(session_id, {})
                    for idx, msg in enumerate(msgs):
                        if idx in ts_map:
                            msg["timestamp"] = ts_map[idx]

                    return {"messages": msgs}
    except Exception:
        pass
    return {"messages": []}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.delete(f"{settings.AGENT_BOX_URL}/sessions/{session_id}", headers=await _headers(), timeout=10)
    _activity.pop(session_id, None)
    return r.json()


@router.post("/{session_id}/send")
async def send_to_session(session_id: str, body: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.AGENT_BOX_URL}/sessions/{session_id}/send",
            headers=await _headers(),
            json=body,
            timeout=10,
        )
    _touch(session_id)
    return r.json()


@router.post("/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{settings.AGENT_BOX_URL}/sessions/{session_id}/interrupt", headers=await _headers(), timeout=10)
    return r.json()
