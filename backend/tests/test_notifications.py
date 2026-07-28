import pytest
import asyncio
import json
from httpx import AsyncClient
from app.core.queue import retry_counts

async def get_user_info_and_headers(
    client: AsyncClient,
    email: str,
    password: str,
    name: str = "Test User"
) -> tuple[dict, dict]:
    reg_data = {
        "email": email,
        "password": password,
        "name": name,
        "skill_level": "Intermediate",
        "city": "Mumbai"
    }
    reg_response = await client.post("/auth/register", json=reg_data)
    user_info = reg_response.json()
    
    login_data = {
        "username": email,
        "password": password
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    token = login_response.json()["access_token"]
    return user_info, {"Authorization": f"Bearer {token}"}

async def test_register_device_token(client: AsyncClient):
    user_info, headers = await get_user_info_and_headers(client, "user_token@example.com", "pass123")
    
    # Register token
    token_data = {
        "token": "token_123456",
        "platform": "ios"
    }
    res = await client.post("/notifications/tokens", json=token_data, headers=headers)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["token"] == "token_123456"
    assert res_data["platform"] == "ios"
    assert res_data["user_id"] == user_info["id"]
    
    # Re-register same token (update owner/platform)
    token_data_update = {
        "token": "token_123456",
        "platform": "android"
    }
    res_update = await client.post("/notifications/tokens", json=token_data_update, headers=headers)
    assert res_update.status_code == 201
    assert res_update.json()["platform"] == "android"

async def test_end_to_end_notifications_pipeline(client: AsyncClient):
    # Register User A (joiner) and User B (host)
    user_a_info, user_a_headers = await get_user_info_and_headers(client, "joiner@example.com", "pass123", "User A")
    user_b_info, user_b_headers = await get_user_info_and_headers(client, "host_notify@example.com", "pass123", "User B")
    
    # User B registers a device token
    token_data = {"token": "host_push_token", "platform": "web"}
    await client.post("/notifications/tokens", json=token_data, headers=user_b_headers)
    
    # Host creates a game
    game_res = await client.post(
        "/games",
        json={"sport": "Football", "city": "Mumbai", "max_players": 5},
        headers=user_b_headers
    )
    assert game_res.status_code == 201
    game_id = game_res.json()["id"]
    
    # User A joins the game (triggers notification)
    join_res = await client.post(f"/games/{game_id}/join", headers=user_a_headers)
    assert join_res.status_code == 200
    
    # Wait for the background worker to consume task from Redis and execute
    await asyncio.sleep(0.5)
    
    # Fetch notifications for Host (User B)
    notif_res = await client.get("/notifications", headers=user_b_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) == 1
    
    notif = notifs[0]
    assert notif["title"] == "Player Joined"
    assert "User A has joined" in notif["body"]
    assert notif["type"] == "join"
    assert notif["read"] is False
    
    # Mark as read
    notif_id = notif["id"]
    read_res = await client.post(f"/notifications/{notif_id}/read", headers=user_b_headers)
    assert read_res.status_code == 200
    assert read_res.json()["read"] is True

async def test_booking_and_payment_notifications(client: AsyncClient, mock_razorpay):
    user_info, headers = await get_user_info_and_headers(client, "booker@example.com", "pass123", "Booker")
    
    # Create venue
    venue_data = {
        "name": "Super Turf", "address": "Bandra", "city": "Mumbai",
        "sports": ["Football"], "hourly_rate": 1000.0,
        "opening_time": "06:00:00", "closing_time": "22:00:00",
        "lat": 19.076, "lng": 72.877
    }
    venue_res = await client.post("/venues", json=venue_data, headers=headers)
    venue_id = venue_res.json()["id"]
    
    # Book the venue (triggers "Booking Reserved" notification)
    booking_data = {
        "venue_id": venue_id,
        "starts_at": "2026-06-07T08:00:00",
        "ends_at": "2026-06-07T10:00:00"
    }
    booking_res = await client.post("/bookings", json=booking_data, headers=headers)
    assert booking_res.status_code == 201
    booking_id = booking_res.json()["id"]
    
    # Pay order generation (creates pending payment, does not trigger confirmation yet)
    pay_res = await client.post(f"/bookings/{booking_id}/pay", headers=headers)
    assert pay_res.status_code == 200
    order_id = pay_res.json()["order"]["id"]
    
    # Wait for the worker to process the booking reservation notification
    await asyncio.sleep(0.5)
    
    # Verify Booker has "Booking Reserved" notification
    notif_res = await client.get("/notifications", headers=headers)
    notifs = notif_res.json()
    assert len(notifs) == 1
    assert notifs[0]["title"] == "Booking Reserved"
    assert notifs[0]["type"] == "booking"
    
    # Simulate Razorpay payment captured callback (triggers "Booking Confirmed" notification)
    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_mock_123",
                    "order_id": order_id,
                    "amount": 200000,
                    "currency": "INR"
                }
            }
        }
    }
    # Webhook signature is validated using secret. Under config, RAZORPAY_WEBHOOK_SECRET = "dummy_webhook_secret".
    # We can mock/bypass or use a valid HMAC signature since it's verified in payments router.
    # Let's generate signature or use razorpay utility
    import hmac
    import hashlib
    body_str = json.dumps(webhook_payload)
    sig = hmac.new(
        b"dummy_webhook_secret",
        body_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    webhook_headers = {"X-Razorpay-Signature": sig}
    webhook_res = await client.post("/payments/webhook", content=body_str, headers=webhook_headers)
    assert webhook_res.status_code == 200
    
    # Wait for background processing
    await asyncio.sleep(0.5)
    
    # Verify Booker has received the second notification "Booking Confirmed"
    notif_res2 = await client.get("/notifications", headers=headers)
    notifs2 = notif_res2.json()
    assert len(notifs2) == 2
    # Sorted by created_at desc, so the first index is the newest notification
    assert notifs2[0]["title"] == "Booking Confirmed"
    assert notifs2[0]["type"] == "payment"

async def test_notifications_retry_with_backoff(client: AsyncClient):
    # Create user with a failing email address (email = fail@example.com triggers exception)
    user_info, headers = await get_user_info_and_headers(client, "fail@example.com", "pass123", "Failing User")
    
    # Register a device token that fails ("fail_token" triggers exception)
    token_data = {"token": "fail_token", "platform": "android"}
    await client.post("/notifications/tokens", json=token_data, headers=headers)
    
    # Create game as host to trigger a create notification if we want, or just trigger any notification.
    # To trigger a join, let's create a game and join it with a different player.
    joiner_info, joiner_headers = await get_user_info_and_headers(client, "joiner_retry@example.com", "pass123", "Joiner")
    game_res = await client.post(
        "/games",
        json={"sport": "Football", "city": "Mumbai", "max_players": 5},
        headers=headers
    )
    game_id = game_res.json()["id"]
    
    # Reset retry tracking counts
    retry_counts.clear()
    
    # Join the game (triggers notify task for fail@example.com host)
    await client.post(f"/games/{game_id}/join", headers=joiner_headers)
    
    # Wait a slightly longer time for retries to execute (delay = 0.1, 0.2, 0.4 seconds)
    # Total wait: 0.1 + 0.2 + 0.4 = 0.7s + sleep buffers
    await asyncio.sleep(2.5)
    
    # Check that retry count for fail@example.com is 4 (1 initial + 3 retries)
    assert retry_counts.get("fail@example.com") == 4
    # Check that retry count for fail_token is 4 (1 initial + 3 retries)
    assert retry_counts.get("fail_token") == 4
