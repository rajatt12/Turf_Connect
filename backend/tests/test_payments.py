import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from app.models import Booking, Payment
from sqlmodel import select

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

# mock_razorpay is now imported from conftest.py

async def test_create_payment_order(client: AsyncClient, mock_razorpay):
    headers = await get_auth_headers(client, "pay_creator@example.com", "pass123")
    
    # 1. Create Venue
    venue_res = await client.post("/venues", json={
        "name": "Pay Venue",
        "address": "Colaba",
        "city": "Mumbai",
        "sports": ["Football"],
        "hourly_rate": 1000.0,
        "opening_time": "09:00:00",
        "closing_time": "21:00:00",
        "lat": 19.01,
        "lng": 72.84
    }, headers=headers)
    venue_id = venue_res.json()["id"]
    
    # 2. Create Booking (2 hours -> 2000 INR)
    booking_res = await client.post("/bookings", json={
        "venue_id": venue_id,
        "starts_at": "2026-06-08T10:00:00",
        "ends_at": "2026-06-08T12:00:00"
    }, headers=headers)
    booking_id = booking_res.json()["id"]
    
    # 3. Pay for Booking
    pay_res = await client.post(f"/bookings/{booking_id}/pay", headers=headers)
    assert pay_res.status_code == 200
    res_data = pay_res.json()
    
    # Assertions
    assert "payment" in res_data
    assert "order" in res_data
    assert res_data["payment"]["status"] == "pending"
    assert res_data["payment"]["amount"] == 2000.0
    assert res_data["payment"]["gateway_order_id"] == "order_test123"
    assert res_data["order"]["id"] == "order_test123"
    
    # Verify mock was called correctly
    mock_razorpay.order.create.assert_called_once_with(data={
        "amount": 200000, # 2000 INR in paise
        "currency": "INR",
        "receipt": f"receipt_{booking_id}",
        "payment_capture": 1
    })

async def test_webhook_payment_captured_success(client: AsyncClient, mock_razorpay, db_session):
    headers = await get_auth_headers(client, "pay_webhook@example.com", "pass123")
    
    # Create Venue & Booking & Payment
    venue_res = await client.post("/venues", json={
        "name": "Webhook Venue",
        "address": "Colaba",
        "city": "Mumbai",
        "sports": ["Football"],
        "hourly_rate": 500.0,
        "opening_time": "09:00:00",
        "closing_time": "21:00:00",
        "lat": 19.01,
        "lng": 72.84
    }, headers=headers)
    venue_id = venue_res.json()["id"]
    
    booking_res = await client.post("/bookings", json={
        "venue_id": venue_id,
        "starts_at": "2026-06-08T14:00:00",
        "ends_at": "2026-06-08T16:00:00"
    }, headers=headers)
    booking_id = booking_res.json()["id"]
    
    # Pay to trigger database row insertion
    await client.post(f"/bookings/{booking_id}/pay", headers=headers)
    
    # Fire Webhook payment capture event
    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "order_id": "order_test123",
                    "id": "pay_captured123"
                }
            }
        }
    }
    
    webhook_headers = {"X-Razorpay-Signature": "valid_signature_mock"}
    webhook_res = await client.post("/payments/webhook", json=webhook_payload, headers=webhook_headers)
    assert webhook_res.status_code == 200
    
    # Clear session to read fresh database values
    db_session.expire_all()
    
    # Verify booking status changed to paid
    booking_db = await db_session.get(Booking, booking_id)
    assert booking_db.status == "paid"
    
    # Verify payment status changed to successful
    stmt = select(Payment).where(Payment.gateway_order_id == "order_test123")
    res = await db_session.execute(stmt)
    payment_db = res.scalar_one()
    assert payment_db.status == "successful"
    assert payment_db.gateway_payment_id == "pay_captured123"

async def test_webhook_idempotence(client: AsyncClient, mock_razorpay, db_session):
    headers = await get_auth_headers(client, "pay_idem@example.com", "pass123")
    
    # Setup venue, booking, payment
    venue_res = await client.post("/venues", json={
        "name": "Idem Venue", "address": "a", "city": "Mumbai", "sports": ["Football"], "hourly_rate": 500.0,
        "opening_time": "09:00:00", "closing_time": "21:00:00", "lat": 19.0, "lng": 72.0
    }, headers=headers)
    venue_id = venue_res.json()["id"]
    
    booking_res = await client.post("/bookings", json={
        "venue_id": venue_id, "starts_at": "2026-06-08T14:00:00", "ends_at": "2026-06-08T16:00:00"
    }, headers=headers)
    booking_id = booking_res.json()["id"]
    
    await client.post(f"/bookings/{booking_id}/pay", headers=headers)
    
    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "order_id": "order_test123",
                    "id": "pay_captured123"
                }
            }
        }
    }
    
    webhook_headers = {"X-Razorpay-Signature": "sig"}
    
    # First delivery
    res1 = await client.post("/payments/webhook", json=webhook_payload, headers=webhook_headers)
    assert res1.status_code == 200
    
    # Second duplicate delivery
    res2 = await client.post("/payments/webhook", json=webhook_payload, headers=webhook_headers)
    assert res2.status_code == 200
    assert res2.json()["message"] == "Already processed"

async def test_webhook_signature_failure(client: AsyncClient, mock_razorpay):
    # Setup mock to raise signature validation exception
    mock_razorpay.utility.verify_webhook_signature.side_effect = Exception("Signature check failed")
    
    webhook_payload = {"event": "payment.captured"}
    webhook_headers = {"X-Razorpay-Signature": "invalid_signature"}
    
    res = await client.post("/payments/webhook", json=webhook_payload, headers=webhook_headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid webhook signature"
