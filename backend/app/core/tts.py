import json as json_mod

from fastapi import WebSocket

# App-level state
tts_clients: set[WebSocket] = set()
played_tts_urls: set[str] = set()


async def broadcast_tts_url(url: str) -> None:
    dead: set[WebSocket] = set()
    for client in tts_clients:
        try:
            await client.send_json({"url": url})
        except Exception:
            dead.add(client)
    tts_clients.difference_update(dead)


def extract_tts_url(payload) -> str | None:
    """Recursively search for an HTTP(S) URL in an arbitrary JSON payload."""
    if isinstance(payload, str):
        if payload.startswith("http://") or payload.startswith("https://"):
            return payload
        try:
            return extract_tts_url(json_mod.loads(payload))
        except Exception:
            return None

    if isinstance(payload, list):
        for item in payload:
            url = extract_tts_url(item)
            if url:
                return url
        return None

    if not isinstance(payload, dict):
        return None

    for key in ("url", "result", "audio_url", "output", "text"):
        value = payload.get(key)
        if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
            return value

    for key in ("tool_response", "tool_result", "result", "structuredContent", "content", "payload", "Ok"):
        if key in payload:
            url = extract_tts_url(payload[key])
            if url:
                return url

    return None
