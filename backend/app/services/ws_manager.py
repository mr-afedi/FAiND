"""
In-memory WebSocket connection manager (Section 14.7).

Keyed by conversation_id → user_id → WebSocket. Redis deferred to v2.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import WebSocket


class ChatConnectionManager:
    def __init__(self) -> None:
        # conversation_id -> { user_id: WebSocket }
        self._rooms: dict[str, dict[str, WebSocket]] = {}

    async def connect(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        key = str(conversation_id)
        if key not in self._rooms:
            self._rooms[key] = {}
        self._rooms[key][str(user_id)] = websocket

    def disconnect(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        key = str(conversation_id)
        room = self._rooms.get(key)
        if not room:
            return
        room.pop(str(user_id), None)
        if not room:
            self._rooms.pop(key, None)

    async def broadcast(
        self,
        conversation_id: uuid.UUID,
        payload: dict[str, Any],
        *,
        exclude_user_id: uuid.UUID | None = None,
    ) -> None:
        key = str(conversation_id)
        room = self._rooms.get(key)
        if not room:
            return
        text = json.dumps(payload, default=str)
        dead: list[str] = []
        for uid, ws in room.items():
            if exclude_user_id and uid == str(exclude_user_id):
                continue
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(uid)
        for uid in dead:
            room.pop(uid, None)

    def is_user_connected(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        return str(user_id) in self._rooms.get(str(conversation_id), {})


chat_manager = ChatConnectionManager()
