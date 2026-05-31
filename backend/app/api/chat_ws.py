"""
WebSocket chat — real-time messages and read receipts (Section 14.7).
"""
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.deps import get_user_from_token
from app.schemas.message import SendMessageRequest
from app.services import chat_service

router = APIRouter(tags=["chat-ws"])


@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    token: str = Query(...),
):
    db: Session = SessionLocal()
    user = None
    try:
        try:
            user = get_user_from_token(db, token)
            chat_service._get_conversation_for_user(db, conversation_id, user.id)
        except HTTPException as exc:
            await websocket.close(code=1008, reason=str(exc.detail))
            return

        from app.services.ws_manager import chat_manager

        await chat_manager.connect(conversation_id, user.id, websocket)

        await chat_service.mark_read_and_notify(db, conversation_id, user)

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "detail": "Invalid JSON"})
                )
                continue

            msg_type = data.get("type")
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "send":
                body = (data.get("body") or "").strip()
                if not body:
                    await websocket.send_text(
                        json.dumps({"type": "error", "detail": "Empty message"})
                    )
                    continue
                try:
                    response = chat_service.send_message(
                        db,
                        conversation_id,
                        user,
                        SendMessageRequest(body=body),
                    )
                    await websocket.send_text(
                        json.dumps(
                            {"type": "new_message", "message": response.model_dump(mode="json")},
                            default=str,
                        )
                    )
                    await chat_service.broadcast_message_event(
                        conversation_id, response, user.id
                    )
                except HTTPException as exc:
                    await websocket.send_text(
                        json.dumps({"type": "error", "detail": exc.detail}, default=str)
                    )
                except Exception as exc:
                    await websocket.send_text(
                        json.dumps({"type": "error", "detail": str(exc)}, default=str)
                    )
                continue

            if msg_type == "mark_read":
                await chat_service.mark_read_and_notify(db, conversation_id, user)
                continue

    except WebSocketDisconnect:
        pass
    finally:
        if user is not None:
            from app.services.ws_manager import chat_manager

            chat_manager.disconnect(conversation_id, user.id)
        db.close()
