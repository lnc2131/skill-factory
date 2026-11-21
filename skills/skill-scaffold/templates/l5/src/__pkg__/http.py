"""{{title}} hosted MCP server (Streamable HTTP) behind API keys.

Keys: set {{PKG}}_API_KEYS to a comma-separated list (make one with `{{name}} new-key`).
Clients send a key one of two ways:
- `Authorization: Bearer <key>`: the Claude Code plugin (.mcp.json) does this.
- In the URL, `https://host/mcp/<key>`: for claude.ai custom connectors, which can't send headers.
"""

from __future__ import annotations

import hmac
import json
import logging
import os

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from .server import build


def _keys() -> list[str]:
    return [k.strip() for k in os.environ.get("{{PKG}}_API_KEYS", "").split(",") if k.strip()]


def _valid(key: str) -> bool:
    return bool(key) and any(hmac.compare_digest(key, k) for k in _keys())


class KeyAuth:
    """Checks the key on every /mcp request; rewrites /mcp/<key> to /mcp for the MCP app."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            path = scope["path"].rstrip("/")
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            auth = headers.get("authorization", "")
            key = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
            if path.startswith("/mcp/"):
                key = path[len("/mcp/"):]
                scope = dict(scope, path="/mcp", raw_path=b"/mcp")
            if not _valid(key):
                body = json.dumps({"error": "invalid_api_key"}).encode()
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def app():
    host = os.environ.get("{{PKG}}_HOST", "127.0.0.1")
    public = os.environ.get("{{PKG}}_PUBLIC_HOST", "")  # e.g. my-mac.tailnet.ts.net
    allowed = ["127.0.0.1:*", "localhost:*"] + ([public, f"{public}:*"] if public else [])
    mcp = build()

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    inner = mcp.streamable_http_app(streamable_http_path="/mcp", host=host,
                                    transport_security=TransportSecuritySettings(allowed_hosts=allowed))
    return KeyAuth(inner)


def serve() -> None:
    logging.basicConfig(level=logging.INFO)
    if not _keys():
        raise SystemExit("Set {{PKG}}_API_KEYS first (comma-separated). Make one with: {{name}} new-key")
    uvicorn.run(app(), host=os.environ.get("{{PKG}}_HOST", "127.0.0.1"),
                port=int(os.environ.get("{{PKG}}_PORT", "8765")))
