"""
AI-HRMS — WebSocket Connection Manager.

Maintains a per-tenant dict of active WebSocket connections.
Thread-safe for single-process; for multi-worker deployments,
replace with a Redis pub/sub backend.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing      import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages all active WebSocket connections scoped by tenant.

    Structure:
        _connections[tenant_id] = {websocket: user_id, ...}
        _user_sockets[user_id]  = [websocket, ...]
    """

    def __init__(self) -> None:
        # tenant_id → set of active WebSocket objects
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        # websocket → (tenant_id, user_id)
        self._meta: dict[WebSocket, tuple[str, str]] = {}
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        user_id:   str,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[tenant_id].add(websocket)
            self._meta[websocket] = (tenant_id, user_id)
        logger.debug(
            "WS connected: user=%s tenant=%s total_in_tenant=%d",
            user_id, tenant_id, len(self._connections[tenant_id]),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            meta = self._meta.pop(websocket, None)
            if meta:
                tenant_id, user_id = meta
                self._connections[tenant_id].discard(websocket)
                if not self._connections[tenant_id]:
                    del self._connections[tenant_id]
                logger.debug(
                    "WS disconnected: user=%s tenant=%s", user_id, tenant_id
                )

    # ── Sending ───────────────────────────────────────────────────────────────

    async def broadcast_to_tenant(
        self,
        tenant_id: str,
        message:   dict[str, Any],
    ) -> None:
        """Send JSON message to every connection in the tenant."""
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []

        sockets = set(self._connections.get(tenant_id, set()))
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.debug("WS send failed (%s); marking for cleanup", exc)
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def send_personal(
        self,
        websocket: WebSocket,
        message:   dict[str, Any],
    ) -> None:
        """Send to a single connection."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as exc:
            logger.debug("WS personal send failed: %s", exc)
            await self.disconnect(websocket)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def active_count(self, tenant_id: str) -> int:
        return len(self._connections.get(tenant_id, set()))

    def all_tenants(self) -> list[str]:
        return list(self._connections.keys())


# ── Module-level singleton ────────────────────────────────────────────────────

manager: ConnectionManager = ConnectionManager()
