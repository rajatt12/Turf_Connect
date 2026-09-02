import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.db import get_db, engine

def get_user_token(tc: TestClient, email: str, password: str) -> str:
    # Helper to register and login a user and return the JWT token
    reg_data = {
        "email": email,
        "password": password,
        "name": "Test User",
        "skill_level": "Beginner",
        "city": "Mumbai"
    }
    tc.post("/auth/register", json=reg_data)
    
    login_data = {
        "username": email,
        "password": password
    }
    login_response = tc.post("/auth/jwt/login", data=login_data)
    return login_response.json()["access_token"]

def test_chat_websocket_connection_and_auth(db_session):
    with TestClient(app) as tc:
        token = get_user_token(tc, "chat1@example.com", "pass123")
        
        # Create Game
        headers = {"Authorization": f"Bearer {token}"}
        game_res = tc.post("/games", json={
            "sport": "Tennis",
            "city": "Mumbai",
            "max_players": 4
        }, headers=headers)
        game_id = game_res.json()["id"]

        # Override get_db to return fresh sessions from global engine
        local_session_maker = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        async def _get_fresh_db():
            async with local_session_maker() as session:
                yield session
        app.dependency_overrides[get_db] = _get_fresh_db
        
        # Happy Path connection & sending/receiving message
        with tc.websocket_connect(f"/ws/games/{game_id}/chat?token={token}") as ws:
            ws.send_json({"body": "Hello chat room!"})
            data = ws.receive_json()
            assert data["body"] == "Hello chat room!"
            assert data["user_name"] == "Test User"
            assert data["game_id"] == game_id
            
        # Authentication Failure: Connection should be closed
        with pytest.raises(Exception):
            with tc.websocket_connect(f"/ws/games/{game_id}/chat?token=invalid_token") as ws:
                ws.receive_json()

    app.dependency_overrides.clear()
    time.sleep(0.2) # Allow background threads to release DB connections

def test_chat_broadcast_multiple_clients(db_session):
    with TestClient(app) as tc:
        token1 = get_user_token(tc, "chat2_1@example.com", "pass123")
        token2 = get_user_token(tc, "chat2_2@example.com", "pass123")
        
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        game_res = tc.post("/games", json={
            "sport": "Football",
            "city": "Mumbai",
            "max_players": 10
        }, headers=headers1)
        game_id = game_res.json()["id"]
        
        # User 2 joins the game
        tc.post(f"/games/{game_id}/join", headers=headers2)
        
        # Override get_db to return fresh sessions from global engine
        local_session_maker = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        async def _get_fresh_db():
            async with local_session_maker() as session:
                yield session
        app.dependency_overrides[get_db] = _get_fresh_db
        
        # Connect User 1 and User 2 to the same game chat room
        with tc.websocket_connect(f"/ws/games/{game_id}/chat?token={token1}") as ws1:
            with tc.websocket_connect(f"/ws/games/{game_id}/chat?token={token2}") as ws2:
                # User 1 sends message
                ws1.send_json({"body": "Hello everyone!"})
                
                # User 2 receives message broadcast in real-time
                data2 = ws2.receive_json()
                assert data2["body"] == "Hello everyone!"
                assert data2["user_name"] == "Test User"
                
                # User 1 also receives echo broadcast
                data1 = ws1.receive_json()
                assert data1["body"] == "Hello everyone!"
                
    app.dependency_overrides.clear()
    time.sleep(0.2) # Allow background threads to release DB connections

def test_chat_history_replay(db_session):
    with TestClient(app) as tc:
        token = get_user_token(tc, "chat3@example.com", "pass123")
        
        headers = {"Authorization": f"Bearer {token}"}
        game_res = tc.post("/games", json={
            "sport": "Badminton",
            "city": "Mumbai",
            "max_players": 2
        }, headers=headers)
        game_id = game_res.json()["id"]
        
        # Override get_db to return fresh sessions from global engine
        local_session_maker = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        async def _get_fresh_db():
            async with local_session_maker() as session:
                yield session
        app.dependency_overrides[get_db] = _get_fresh_db
        
        # First connection: send message, then close
        with tc.websocket_connect(f"/ws/games/{game_id}/chat?token={token}") as ws:
            ws.send_json({"body": "Replay message 1"})
            # Wait for broadcast echo back to ensure it is committed to DB
            ws.receive_json()
            
        # Reconnection: verify history message is replayed immediately on connect
        with tc.websocket_connect(f"/ws/games/{game_id}/chat?token={token}") as ws:
            data = ws.receive_json()
            assert data["body"] == "Replay message 1"
            assert data["user_name"] == "Test User"
            
    app.dependency_overrides.clear()
    time.sleep(0.2) # Allow background threads to release DB connections
