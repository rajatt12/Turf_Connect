import uuid
import json
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.db import get_db
from app.models import User, Game, Message

router = APIRouter(tags=["chat"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[uuid.UUID, List[WebSocket]] = {}

    async def connect(self, game_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append(websocket)

    def disconnect(self, game_id: uuid.UUID, websocket: WebSocket):
        if game_id in self.active_connections:
            self.active_connections[game_id].remove(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast(self, game_id: uuid.UUID, message: dict):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/games/{game_id}/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # 1. Retrieve the authentication token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    # Get user manager
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
    from app.core.users import UserManager, get_jwt_strategy
    user_db = SQLAlchemyUserDatabase(db, User)
    user_manager = UserManager(user_db)
    
    # 2. Authenticate the connecting User
    strategy = get_jwt_strategy()
    user = await strategy.read_token(token, user_manager)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    # 3. Verify the target game exists
    game = await db.get(Game, game_id)
    if not game:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 4. Accept connection and register
    await manager.connect(game_id, websocket)
    
    try:
        # 5. Replay history (last 50 messages, chronological order)
        history_stmt = (
            select(Message)
            .where(Message.game_id == game_id)
            .options(selectinload(Message.user))
            .order_by(Message.created_at.desc())
            .limit(50)
        )
        history_res = await db.execute(history_stmt)
        history = history_res.scalars().all()
        history.reverse() # Oldest first
        
        for msg in history:
            await websocket.send_json({
                "id": str(msg.id),
                "game_id": str(msg.game_id),
                "user_id": str(msg.user_id),
                "user_name": msg.user.name if msg.user else "Unknown User",
                "body": msg.body,
                "created_at": msg.created_at.isoformat()
            })
            
        # 6. Message Loop
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                body = payload.get("body")
            except Exception:
                continue  # Ignore invalid JSON
                
            if not body:
                continue
                
            # Save message in DB
            db_msg = Message(
                game_id=game_id,
                user_id=user.id,
                body=body
            )
            db.add(db_msg)
            await db.commit()
            await db.refresh(db_msg)
            
            # Broadcast payload matching MessageRead
            broadcast_payload = {
                "id": str(db_msg.id),
                "game_id": str(db_msg.game_id),
                "user_id": str(db_msg.user_id),
                "user_name": user.name,
                "body": db_msg.body,
                "created_at": db_msg.created_at.isoformat()
            }
            await manager.broadcast(game_id, broadcast_payload)
            
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(game_id, websocket)
