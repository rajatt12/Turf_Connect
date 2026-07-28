import pytest
from httpx import AsyncClient

async def test_auth_flow(client: AsyncClient):
    """Test the complete authentication flow: registration, login, and profile access."""
    # 1. Register a new user
    reg_data = {
        "email": "testuser@example.com",
        "password": "testpassword123",
        "name": "Test User",
        "skill_level": "Beginner",
        "city": "Mumbai"
    }
    reg_response = await client.post("/auth/register", json=reg_data)
    assert reg_response.status_code == 201
    user_info = reg_response.json()
    assert user_info["email"] == "testuser@example.com"
    assert user_info["name"] == "Test User"
    assert user_info["skill_level"] == "Beginner"
    assert user_info["city"] == "Mumbai"
    assert "id" in user_info

    # 2. Login with registered credentials to receive JWT token
    # fastapi-users / OAuth2 uses form-encoded data for login (username & password)
    login_data = {
        "username": "testuser@example.com",
        "password": "testpassword123"
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]

    # 3. Retrieve user profile from protected endpoint (/users/me) using token
    headers = {"Authorization": f"Bearer {token}"}
    me_response = await client.get("/users/me", headers=headers)
    assert me_response.status_code == 200
    me_info = me_response.json()
    assert me_info["email"] == "testuser@example.com"
    assert me_info["name"] == "Test User"
    assert me_info["city"] == "Mumbai"
    assert me_info["skill_level"] == "Beginner"
    assert me_info["role"] == "player" # Default role
