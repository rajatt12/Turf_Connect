import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, Venue, Booking, BookingCreate, BookingRead

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_in: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # 1. Validate booking dates order
    if booking_in.starts_at >= booking_in.ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="starts_at must be before ends_at"
        )
        
    # 2. Lock the parent Venue row using pessimistic locking (SELECT ... FOR UPDATE)
    venue_stmt = select(Venue).where(Venue.id == booking_in.venue_id).with_for_update()
    venue_res = await db.execute(venue_stmt)
    venue = venue_res.scalar_one_or_none()
    
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found"
        )
        
    # 3. Check venue operating hours
    start_time = booking_in.starts_at.time()
    end_time = booking_in.ends_at.time()
    
    if start_time < venue.opening_time or end_time > venue.closing_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking slot must be within venue operating hours"
        )
        
    # 4. Check for overlapping bookings
    overlap_stmt = select(Booking).where(
        Booking.venue_id == booking_in.venue_id,
        Booking.status != "cancelled",
        Booking.starts_at < booking_in.ends_at,
        Booking.ends_at > booking_in.starts_at
    )
    overlap_res = await db.execute(overlap_stmt)
    existing_overlap = overlap_res.scalars().first()
    
    if existing_overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Double-booking! This venue is already booked for the requested time slot."
        )
        
    # 5. Create and save the booking
    db_booking = Booking(
        venue_id=booking_in.venue_id,
        user_id=current_user.id,
        starts_at=booking_in.starts_at,
        ends_at=booking_in.ends_at,
        status="unpaid"
    )
    db.add(db_booking)
    await db.commit()
    await db.refresh(db_booking)
    
    # Notify user that booking is reserved
    from app.core.queue import enqueue_task
    await enqueue_task(
        "send_notification",
        str(current_user.id),
        "Booking Reserved",
        f"Your booking at venue is reserved. Please pay to confirm.",
        "booking"
    )
    
    return db_booking

@router.get("", response_model=List[BookingRead])
async def list_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # If admin, return all bookings; otherwise, only current user's bookings
    if current_user.role == "admin":
        stmt = select(Booking)
    else:
        stmt = select(Booking).where(Booking.user_id == current_user.id)
        
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{id}", response_model=BookingRead)
async def get_booking(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    db_booking = await db.get(Booking, id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
        
    # Allow details access only if it's the owner or an admin
    if db_booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this booking"
        )
        
    return db_booking

@router.post("/{id}/cancel", response_model=BookingRead)
async def cancel_booking(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    db_booking = await db.get(Booking, id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
        
    # Only owner or admin can cancel
    if db_booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this booking"
        )
        
    if db_booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled"
        )
        
    db_booking.status = "cancelled"
    db.add(db_booking)
    await db.commit()
    await db.refresh(db_booking)
    return db_booking
