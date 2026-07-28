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

async def test_venue_crud(client: AsyncClient):
    headers = await get_auth_headers(client, "user_venue_crud@example.com", "pass123")
    
    # 1. Create Venue
    venue_data = {
        "name": "Turf Park",
        "address": "Andheri West",
        "city": "Mumbai",
        "sports": ["Football", "Cricket"],
        "hourly_rate": 1500.0,
        "opening_time": "08:00:00",
        "closing_time": "23:00:00",
        "lat": 19.1234,
        "lng": 72.8765
    }
    create_res = await client.post("/venues", json=venue_data, headers=headers)
    assert create_res.status_code == 201
    created_venue = create_res.json()
    assert "id" in created_venue
    assert created_venue["name"] == "Turf Park"
    assert created_venue["sports"] == ["Football", "Cricket"]
    venue_id = created_venue["id"]
    
    # 2. Get Venue Details
    get_res = await client.get(f"/venues/{venue_id}")
    assert get_res.status_code == 200
    assert get_res.json()["address"] == "Andheri West"
    
    # 3. Update Venue
    update_data = {
        "name": "Updated Turf Park",
        "hourly_rate": 1800.0
    }
    update_res = await client.put(f"/venues/{venue_id}", json=update_data, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Turf Park"
    assert update_res.json()["hourly_rate"] == 1800.0
    
    # 4. Delete Venue
    delete_res = await client.delete(f"/venues/{venue_id}", headers=headers)
    assert delete_res.status_code == 204
    
    # 5. Verify Deleted
    get_deleted = await client.get(f"/venues/{venue_id}")
    assert get_deleted.status_code == 404

async def test_list_and_filter_venues(client: AsyncClient):
    headers = await get_auth_headers(client, "user_venue_filter@example.com", "pass123")
    
    # Create Venue 1 (Mumbai - Football & Cricket)
    await client.post("/venues", json={
        "name": "Mumbai Turf",
        "address": "Bandra",
        "city": "Mumbai",
        "sports": ["Football", "Cricket"],
        "hourly_rate": 1200.0,
        "opening_time": "06:00:00",
        "closing_time": "22:00:00",
        "lat": 19.05,
        "lng": 72.83
    }, headers=headers)
    
    # Create Venue 2 (Pune - Tennis)
    await client.post("/venues", json={
        "name": "Pune Club",
        "address": "Deccan",
        "city": "Pune",
        "sports": ["Tennis"],
        "hourly_rate": 800.0,
        "opening_time": "07:00:00",
        "closing_time": "21:00:00",
        "lat": 18.52,
        "lng": 73.84
    }, headers=headers)
    
    # List all
    res = await client.get("/venues")
    assert res.status_code == 200
    assert len(res.json()) == 2
    
    # Filter by city Bandra is inside Mumbai
    res_mumbai = await client.get("/venues?city=Mumbai")
    assert len(res_mumbai.json()) == 1
    assert res_mumbai.json()[0]["city"] == "Mumbai"
    
    # Filter by sport: Tennis
    res_tennis = await client.get("/venues?sport=Tennis")
    assert len(res_tennis.json()) == 1
    assert res_tennis.json()[0]["name"] == "Pune Club"

async def test_venue_games_nested_listing(client: AsyncClient):
    headers = await get_auth_headers(client, "user_venue_games@example.com", "pass123")
    
    # 1. Create Venue
    venue_res = await client.post("/venues", json={
        "name": "Sports Arena",
        "address": "Koramangala",
        "city": "Bangalore",
        "sports": ["Football", "Badminton"],
        "hourly_rate": 1000.0,
        "opening_time": "09:00:00",
        "closing_time": "21:00:00",
        "lat": 12.93,
        "lng": 77.62
    }, headers=headers)
    venue_id = venue_res.json()["id"]
    
    # 2. Create game referencing this venue
    game_res = await client.post("/games", json={
        "sport": "Football",
        "city": "Bangalore",
        "max_players": 10,
        "venue_id": venue_id
    }, headers=headers)
    assert game_res.status_code == 201
    game_id = game_res.json()["id"]
    
    # 3. Query games nested endpoint
    nested_res = await client.get(f"/venues/{venue_id}/games")
    assert nested_res.status_code == 200
    games = nested_res.json()
    assert len(games) == 1
    assert games[0]["id"] == game_id
    assert games[0]["venue_id"] == venue_id
    
    # Query non-existent venue games
    fake_id = "00000000-0000-0000-0000-000000000000"
    nested_fake_res = await client.get(f"/venues/{fake_id}/games")
    assert nested_fake_res.status_code == 404
