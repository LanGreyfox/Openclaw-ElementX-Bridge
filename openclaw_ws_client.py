#!/usr/bin/env python3
"""Minimal OpenClaw Gateway WebSocket client.

Features:
- connect challenge
- connect handshake
- request/response RPCs
- health / models.list / sessions.list / chat.send examples
- reconnect skeleton

Install:
  python3 -m pip install websockets

Run:
  python3 openclaw_ws_client.py --token YOUR_GATEWAY_TOKEN
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import websockets


WS_URL = os.environ.get("OPENCLAW_WS_URL", "ws://127.0.0.1:18789")


@dataclass
class RpcResult:
    ok: bool
    payload: Any = None
    error: Any = None


class OpenClawClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._pending: Dict[str, asyncio.Future] = {}

    async def connect(self) -> None:
        self.ws = await websockets.connect(self.url, max_size=None)

        first = json.loads(await self.ws.recv())
        if first.get("type") != "event" or first.get("event") != "connect.challenge":
            raise RuntimeError(f"Expected connect.challenge first, got: {first}")

        challenge = first["payload"]
        conn_req_id = str(uuid.uuid4())
        connect_req = {
            "type": "req",
            "id": conn_req_id,
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "gateway-client",
                    "version": "0.1.0",
                    "platform": sys.platform,
                    "mode": "backend",
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {"token": self.token},
                "locale": "de-DE",
                "userAgent": "openclaw-ws-client/0.1.0",
            },
        }

        await self.ws.send(json.dumps(connect_req))
        hello = json.loads(await self.ws.recv())
        if not hello.get("ok"):
            raise RuntimeError(f"Handshake failed: {hello}")
        if hello.get("payload", {}).get("type") != "hello-ok":
            raise RuntimeError(f"Expected hello-ok, got: {hello}")

    async def request(self, method: str, params: Optional[dict] = None) -> RpcResult:
        if self.ws is None:
            raise RuntimeError("Not connected")

        req_id = str(uuid.uuid4())
        await self.ws.send(json.dumps({"type": "req", "id": req_id, "method": method, "params": params or {}}))

        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("type") == "res" and msg.get("id") == req_id:
                return RpcResult(ok=msg.get("ok", False), payload=msg.get("payload"), error=msg.get("error"))
            if msg.get("type") == "event":
                # Keep it simple: print unsolicited events.
                print("EVENT:", json.dumps(msg, ensure_ascii=False))
                continue
            # Unexpected frame - ignore and keep waiting for our response.

    async def close(self) -> None:
        if self.ws is not None:
            await self.ws.close()
            self.ws = None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True, help="Gateway auth token")
    ap.add_argument("--url", default=WS_URL)
    ap.add_argument("--chat", default=None, help="Optional chat text to send via chat.send")
    args = ap.parse_args()

    client = OpenClawClient(args.url, args.token)

    backoff = 1.0
    for attempt in range(1, 4):
        try:
            await client.connect()
            print("Connected.")

            for method in ("health", "models.list", "sessions.list"):
                result = await client.request(method)
                print(f"\n== {method} ==")
                print(json.dumps(result.payload if result.ok else result.error, indent=2, ensure_ascii=False))

            if args.chat:
                # chat.send requires sessionKey, message, idempotencyKey.
                session_res = await client.request("sessions.list")
                session_key = None
                if session_res.ok and isinstance(session_res.payload, dict):
                    items = session_res.payload.get("sessions") or session_res.payload.get("items") or session_res.payload.get("results") or []
                    if items:
                        first_session = items[0]
                        if isinstance(first_session, dict):
                            session_key = first_session.get("key") or first_session.get("sessionKey") or first_session.get("id")
                if not session_key:
                    raise RuntimeError("Could not resolve a sessionKey from sessions.list; pass one manually or create a session first.")

                result = await client.request("chat.send", {
                    "sessionKey": session_key,
                    "message": args.chat,
                    "idempotencyKey": str(uuid.uuid4()),
                })
                print("\n== chat.send ==")
                print(json.dumps(result.payload if result.ok else result.error, indent=2, ensure_ascii=False))

            await client.close()
            return

        except Exception as e:
            print(f"Attempt {attempt} failed: {e}", file=sys.stderr)
            await client.close()
            if attempt == 3:
                raise
            await asyncio.sleep(backoff)
            backoff *= 2


if __name__ == "__main__":
    asyncio.run(main())