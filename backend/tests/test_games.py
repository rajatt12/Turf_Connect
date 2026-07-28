import pytest
from httpx import AsyncClient

async def get_auth_headers(
    client: AsyncClient,
    email: str,
    password: str,
    name: str = "Test User",
    skill_level: str = "Beginner",
    city: str = "Mumbai"
) -> dict:
    # Helper to register and login a user, returning Authorization headers
    reg_data = {
        "email": email,
        "password": password,
        "name": name,
        "skill_level": skill_level,
        "city": city
    }
    await client.post("/auth/register", json=reg_data)
    
    login_data = {
        "username": email,
        "password": password
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def test_create_game(client: AsyncClient):
    # Get auth headers for User 1
    headers = await get_auth_headers(client, "user1@example.com", "pass123", "User One")
    
    game_data = {
        "sport": "Football",
        "city": "Mumbai",
        "max_players": 5
    }
    response = await client.post("/games", json=game_data, headers=headers)
    assert response.status_code == 201
    
    res_data = response.json()
    assert "id" in res_data
    assert res_data["sport"] == "Football"
    assert res_data["city"] == "Mumbai"
    assert res_data["max_players"] == 5
    assert res_data["status"] == "open"
    assert res_data["slots_filled"] == 1
    assert res_data["slots_open"] == 4
    assert "host_id" in res_data

async def test_get_game_details(client: AsyncClient):
    headers = await get_auth_headers(client, "user2@example.com", "pass123", "User Two")
    
    # Create game
    game_data = {"sport": "Cricket", "city": "Delhi", "max_players": 11}
    create_res = await client.post("/games", json=game_data, headers=headers)
    game_id = create_res.json()["id"]
    
    # Get details
    get_res = await client.get(f"/games/{game_id}")
    assert get_res.status_code == 200
    assert get_res.json()["sport"] == "Cricket"
    assert get_res.json()["city"] == "Delhi"
    
    # Get non-existent game
    fake_id = "00000000-0000-0000-0000-000000000000"
    get_fake_res = await client.get(f"/games/{fake_id}")
    assert get_fake_res.status_code == 404

async def test_list_and_filter_games(client: AsyncClient):
    headers1 = await get_auth_headers(client, "user3@example.com", "pass123")
    headers2 = await get_auth_headers(client, "user4@example.com", "pass123")
    
    # Create Game 1: Football in Mumbai
    await client.post("/games", json={"sport": "Football", "city": "Mumbai", "max_players": 6}, headers=headers1)
    # Create Game 2: Tennis in Mumbai
    await client.post("/games", json={"sport": "Tennis", "city": "Mumbai", "max_players": 2}, headers=headers2)
    # Create Game 3: Football in Pune
    await client.post("/games", json={"sport": "Football", "city": "Pune", "max_players": 10}, headers=headers1)
    
    # Filter by sport: Football
    res = await client.get("/games?sport=Football")
    assert res.status_code == 200
    games = res.json()
    assert len(games) == 2
    assert all(g["sport"] == "Football" for g in games)
    
    # Filter by city: Mumbai
    res = await client.get("/games?city=Mumbai")
    assert res.status_code == 200
    games = res.json()
    assert len(games) == 2
    assert all(g["city"] == "Mumbai" for g in games)
    
    # Filter by sport and city: Tennis in Mumbai
    res = await client.get("/games?sport=Tennis&city=Mumbai")
    assert res.status_code == 200
    games = res.json()
    assert len(games) == 1
    assert games[0]["sport"] == "Tennis"
    
    # Pagination check: Limit 1, Offset 1
    res = await client.get("/games?limit=1&offset=1")
    assert res.status_code == 200
    games = res.json()
    assert len(games) == 1

async def test_join_game_flow(client: AsyncClient):
    headers_host = await get_auth_headers(client, "host@example.com", "pass123")
    headers_player1 = await get_auth_headers(client, "player1@example.com", "pass123")
    headers_player2 = await get_auth_headers(client, "player2@example.com", "pass123")
    
    # Host creates a game of 2 players (Host + 1 player)
    create_res = await client.post("/games", json={"sport": "Badminton", "city": "Bangalore", "max_players": 2}, headers=headers_host)
    game_id = create_res.json()["id"]
    
    # Host tries to join their own game again
    join_self_res = await client.post(f"/games/{game_id}/join", headers=headers_host)
    assert join_self_res.status_code == 409
    assert join_self_res.json()["detail"] == "Already joined this game"
    
    # Player 1 joins game (Happy Path)
    join_res1 = await client.post(f"/games/{game_id}/join", headers=headers_player1)
    assert join_res1.status_code == 200
    data = join_res1.json()
    assert data["slots_filled"] == 2
    assert data["slots_open"] == 0
    assert data["status"] == "full" # Automatically flipped because it's filled
    
    # Player 2 tries to join now full game
    join_res2 = await client.post(f"/games/{game_id}/join", headers=headers_player2)
    assert join_res2.status_code == 409
    assert join_res2.json()["detail"] == "Game is not open"
