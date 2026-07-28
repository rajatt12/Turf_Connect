import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, Notification, NotificationRead, DeviceToken, DeviceTokenCreate, DeviceTokenRead

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/tokens", response_model=DeviceTokenRead, status_code=status.HTTP_201_CREATED)
async def register_token(
    token_in: DeviceTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # Check if token already exists
    statement = select(DeviceToken).where(DeviceToken.token == token_in.token)
    result = await db.execute(statement)
    db_token = result.scalar_one_or_none()
    
    if db_token:
        # Update owner and platform
        db_token.user_id = current_user.id
        db_token.platform = token_in.platform
    else:
        # Create new token record
        db_token = DeviceToken(
            user_id=current_user.id,
            token=token_in.token,
            platform=token_in.platform
        )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


@router.get("", response_model=List[NotificationRead])
async def list_notifications(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    statement = select(Notification).where(Notification.user_id == current_user.id)
    statement = statement.order_by(Notification.created_at.desc())
    statement = statement.offset(offset).limit(limit)
    
    result = await db.execute(statement)
    notifications = result.scalars().all()
    return notifications


@router.post("/{id}/read", response_model=NotificationRead)
async def mark_as_read(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    db_notification = await db.get(Notification, id)
    if not db_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
        
    if db_notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this notification"
        )
        
    db_notification.read = True
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return db_notification
