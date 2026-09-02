import uuid
import json
import razorpay
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.config import settings
from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, Booking, Payment, PaymentRead

router = APIRouter(tags=["payments"])

@router.post("/bookings/{id}/pay", response_model=Dict[str, Any])
async def pay_booking(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # 1. Fetch booking with eagerly loaded venue (to check hourly_rate)
    stmt = select(Booking).where(Booking.id == id).options(selectinload(Booking.venue))
    res = await db.execute(stmt)
    booking = res.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
        
    # Check authorization
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to pay for this booking"
        )
        
    # Check if already paid
    if booking.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already paid"
        )
        
    # 2. Calculate the cost
    duration_hours = (booking.ends_at - booking.starts_at).total_seconds() / 3600.0
    amount = booking.venue.hourly_rate * duration_hours
    
    # 3. Create order in Razorpay (or simulated test order if in dev test mode)
    if settings.RAZORPAY_KEY_ID.startswith("dummy") or not settings.RAZORPAY_KEY_SECRET:
        order = {
            "id": f"order_test_{uuid.uuid4().hex[:12]}",
            "amount": int(amount * 100),
            "currency": "INR",
            "receipt": f"receipt_{booking.id}",
            "status": "created"
        }
    else:
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                "amount": int(amount * 100),  # Amount in paise
                "currency": "INR",
                "receipt": f"receipt_{booking.id}",
                "payment_capture": 1
            }
            order = client.order.create(data=order_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create order with gateway: {str(e)}"
            )
        
    # 4. Save Payment record in database
    db_payment = Payment(
        booking_id=booking.id,
        amount=amount,
        currency="INR",
        gateway_order_id=order["id"],
        status="pending"
    )
    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    
    return {
        "payment": db_payment,
        "order": order
    }

@router.post("/payments/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch headers and request body
    signature = request.headers.get("X-Razorpay-Signature")
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    
    # 2. Verify Razorpay webhook signature (if not in test mode with dummy secrets)
    is_dummy_mode = settings.RAZORPAY_WEBHOOK_SECRET.startswith("dummy")
    if not is_dummy_mode:
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook signature missing"
            )
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_webhook_signature(
                body_str,
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
        
    # 3. Parse webhook payload
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
        
    event = payload.get("event")
    
    # 4. Process event
    if event == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
        
        if not order_id:
            return {"status": "ignored", "reason": "No order_id in payment capture event"}
            
        # Fetch payment record eagerly loading its booking
        stmt = select(Payment).where(Payment.gateway_order_id == order_id).options(selectinload(Payment.booking))
        res = await db.execute(stmt)
        db_payment = res.scalar_one_or_none()
        
        if not db_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment record not found"
            )
            
        # Idempotence: skip if already marked successful
        if db_payment.status == "successful":
            return {"status": "ok", "message": "Already processed"}
            
        # Update statuses
        db_payment.status = "successful"
        db_payment.gateway_payment_id = payment_id
        db.add(db_payment)
        
        booking = db_payment.booking
        if booking:
            booking.status = "paid"
            db.add(booking)
            
        await db.commit()

        # Notify user of successful payment & confirmation
        if booking:
            from app.core.queue import enqueue_task
            await enqueue_task(
                "send_notification",
                str(booking.user_id),
                "Booking Confirmed",
                f"Your booking at venue is confirmed and paid.",
                "payment"
            )
        
    return {"status": "ok"}
