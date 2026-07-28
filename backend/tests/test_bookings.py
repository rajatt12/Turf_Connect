import pytest
import asyncio
from httpx import AsyncClient

async def get_auth_headers(
    client: AsyncClient,
    email: str,
    password: str,
    name: str = "Test User",
    skill_level: str = "Beginner",
    city: str = "Mumbai"
) -> dict:
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

async def test_booking_crud_and_hours_validation(client: AsyncClient):
    headers = await get_auth_headers(client, "booker_crud@example.com", "pass123")
    
    # 1. Create a Venue
    venue_res = await client.post("/venues", json={
        "name": "Booking Club",
        "address": "Dadar",
        "city": "Mumbai",
        "sports": ["Football"],
        "hourly_rate": 1000.0,
        "opening_time": "09:00:00",
        "closing_time": "21:00:00",
        "lat": 19.01,
        "lng": 72.84
    }, headers=headers)
    venue_id = venue_res.json()["id"]
    
    # 2. Try creating booking outside operating hours (starts at 08:00, but venue opens at 09:00)
    booking_out_of_hours = {
        "venue_id": venue_id,
        "starts_at": "2026-06-07T08:00:00",
        "ends_at": "2026-06-07T10:00:00"
    }
    res_bad = await client.post("/bookings", json=booking_out_of_hours, headers=headers)
    assert res_bad.status_code == 400
    assert "operating hours" in res_bad.json()["detail"]
    
    # 3. Create booking (within hours)
    booking_good = {
        "venue_id": venue_id,
        "starts_at": "2026-06-07T10:00:00",
        "ends_at": "2026-06-07T12:00:00"
    }
    res_good = await client.post("/bookings", json=booking_good, headers=headers)
    assert res_good.status_code == 201
    booking_id = res_good.json()["id"]
    assert res_good.json()["status"] == "unpaid"
    
    # 4. Get booking details
    res_get = await client.get(f"/bookings/{booking_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["starts_at"].startswith("2026-06-07T10:00:00")
    
    # 5. Cancel booking
    res_cancel = await client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"

async def test_booking_overlap_prevention(client: AsyncClient):
    headers1 = await get_auth_headers(client, "booker1@example.com", "pass123")
    headers2 = await get_auth_headers(client, "booker2@example.com", "pass123")
    
    # Create Venue
    venue_res = await client.post("/venues", json={
        "name": "Overlap Arena",
        "address": "Worli",
        "city": "Mumbai",
        "sports": ["Football"],
        "hourly_rate": 1000.0,
        "opening_time": "09:00:00",
        "closing_time": "21:00:00",
        "lat": 19.01,
        "lng": 72.84
    }, headers=headers1)
    venue_id = venue_res.json()["id"]
    
    # Booker 1 books 14:00 - 16:00
    b1_data = {
        "venue_id": venue_id,
        "starts_at": "2026-06-07T14:00:00",
        "ends_at": "2026-06-07T16:00:00"
    }
    await client.post("/bookings", json=b1_data, headers=headers1)
    
    # Booker 2 tries to book overlapping slot (15:00 - 17:00)
    b2_data = {
        "venue_id": venue_id,
        "starts_at": "2026-06-07T15:00:00",
        "ends_at": "2026-06-07T17:00:00"
    }
    overlap_res = await client.post("/bookings", json=b2_data, headers=headers2)
    assert overlap_res.status_code == 409
    assert "Double-booking" in overlap_res.json()["detail"]

async def test_booking_concurrency_race_condition(client: AsyncClient, test_engine):
    # Override get_db to return a fresh session for each concurrent request
    from app.core.db import get_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.main import app

    local_session_maker = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async def _get_fresh_db():
        async with local_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_fresh_db

    # Two different users try to book the exact same slot concurrently
    headers1 = await get_auth_headers(client, "race1@example.com", "pass123")
    headers2 = await get_auth_headers(client, "race2@example.com", "pass123")
    
    # Create Venue
    venue_res = await client.post("/venues", json={
        "name": "Race Stadium",
        "address": "Bandra",
        "city": "Mumbai",
        "sports": ["Football"],
        "hourly_rate": 1000.0,
        "opening_time": "09:00:00",
        "closing_time": "21:00:00",
        "lat": 19.01,
        "lng": 72.84
    }, headers=headers1)
    venue_id = venue_res.json()["id"]
    
    booking_data = {
        "venue_id": venue_id,
        "starts_at": "2026-06-07T11:00:00",
        "ends_at": "2026-06-07T13:00:00"
    }
    
    # Dispatch both requests concurrently
    tasks = [
        client.post("/bookings", json=booking_data, headers=headers1),
        client.post("/bookings", json=booking_data, headers=headers2)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    status_codes = [r.status_code for r in responses]
    assert 201 in status_codes
    assert 409 in status_codes
    # Verify that exactly one booking succeeded and the other was rejected
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 1
