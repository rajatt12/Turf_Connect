import pytest
from httpx import AsyncClient

async def get_auth_headers(
    client: AsyncClient,
    email: str,
    password: str,
    name: str = "Test User"
) -> dict:
    reg_data = {
        "email": email,
        "password": password,
        "name": name,
        "skill_level": "Intermediate",
        "city": "Mumbai"
    }
    await client.post("/auth/register", json=reg_data)
    
    login_data = {
        "username": email,
        "password": password
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def test_nearby_games_proximity_and_sorting(client: AsyncClient):
    headers = await get_auth_headers(client, "geo_host@example.com", "pass123")
    
    # 1. Create Venue A (Mumbai Center)
    venue_a_data = {
        "name": "Mumbai Arena",
        "address": "Bandra East",
        "city": "Mumbai",
        "sports": ["Football"],
        "hourly_rate": 1000.0,
        "opening_time": "06:00:00",
        "closing_time": "22:00:00",
        "lat": 19.0760,
        "lng": 72.8777
    }
    venue_a_res = await client.post("/venues", json=venue_a_data, headers=headers)
    assert venue_a_res.status_code == 201
    venue_a_id = venue_a_res.json()["id"]
    
    # 2. Create Venue B (Thane - ~20 km away)
    venue_b_data = {
        "name": "Thane Turf",
        "address": "Wagle Estate",
        "city": "Thane",
        "sports": ["Football"],
        "hourly_rate": 800.0,
        "opening_time": "06:00:00",
        "closing_time": "22:00:00",
        "lat": 19.2183,
        "lng": 72.9781
    }
    venue_b_res = await client.post("/venues", json=venue_b_data, headers=headers)
    assert venue_b_res.status_code == 201
    venue_b_id = venue_b_res.json()["id"]
    
    # 3. Create Venue C (Pune - ~120 km away)
    venue_c_data = {
        "name": "Pune Club",
        "address": "Koregaon Park",
        "city": "Pune",
        "sports": ["Football"],
        "hourly_rate": 1200.0,
        "opening_time": "06:00:00",
        "closing_time": "22:00:00",
        "lat": 18.5204,
        "lng": 73.8567
    }
    venue_c_res = await client.post("/venues", json=venue_c_data, headers=headers)
    assert venue_c_res.status_code == 201
    venue_c_id = venue_c_res.json()["id"]
    
    # Create games at each venue
    game_a_res = await client.post("/games", json={"sport": "Football", "city": "Mumbai", "max_players": 10, "venue_id": venue_a_id}, headers=headers)
    assert game_a_res.status_code == 201
    game_a_id = game_a_res.json()["id"]
    
    game_b_res = await client.post("/games", json={"sport": "Football", "city": "Thane", "max_players": 10, "venue_id": venue_b_id}, headers=headers)
    assert game_b_res.status_code == 201
    game_b_id = game_b_res.json()["id"]
    
    game_c_res = await client.post("/games", json={"sport": "Football", "city": "Pune", "max_players": 10, "venue_id": venue_c_id}, headers=headers)
    assert game_c_res.status_code == 201
    game_c_id = game_c_res.json()["id"]
    
    # --- Proximity test center = Mumbai (19.0760, 72.8777) ---
    
    # Radius = 5 km (Only Venue A is nearby)
    res_5km = await client.get("/games?lat=19.0760&lng=72.8777&radius_km=5.0", headers=headers)
    assert res_5km.status_code == 200
    games_5km = res_5km.json()
    assert len(games_5km) == 1
    assert games_5km[0]["id"] == game_a_id
    
    # Radius = 30 km (Venue A & B should be included, sorted A then B)
    res_30km = await client.get("/games?lat=19.0760&lng=72.8777&radius_km=30.0", headers=headers)
    assert res_30km.status_code == 200
    games_30km = res_30km.json()
    assert len(games_30km) == 2
    assert games_30km[0]["id"] == game_a_id
    assert games_30km[1]["id"] == game_b_id
    
    # Radius = 150 km (All Venue A, B & C should be included, sorted A, B, C)
    res_150km = await client.get("/games?lat=19.0760&lng=72.8777&radius_km=150.0", headers=headers)
    assert res_150km.status_code == 200
    games_150km = res_150km.json()
    assert len(games_150km) == 3
    assert games_150km[0]["id"] == game_a_id
    assert games_150km[1]["id"] == game_b_id
    assert games_150km[2]["id"] == game_c_id


async def test_nearby_games_validation(client: AsyncClient):
    headers = await get_auth_headers(client, "geo_validator@example.com", "pass123")
    
    # 1. Missing radius
    res_no_radius = await client.get("/games?lat=19.0760&lng=72.8777", headers=headers)
    assert res_no_radius.status_code == 400
    assert "all must be provided" in res_no_radius.json()["detail"]
    
    # 2. Missing lat
    res_no_lat = await client.get("/games?lng=72.8777&radius_km=10", headers=headers)
    assert res_no_lat.status_code == 400
    assert "all must be provided" in res_no_lat.json()["detail"]
    
    # 3. Missing lng
    res_no_lng = await client.get("/games?lat=19.0760&radius_km=10", headers=headers)
    assert res_no_lng.status_code == 400
    assert "all must be provided" in res_no_lng.json()["detail"]
