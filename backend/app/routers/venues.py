import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import any_
from sqlmodel import select

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, Venue, VenueCreate, VenueUpdate, VenueRead, Game, GameRead

router = APIRouter(prefix="/venues", tags=["venues"])

@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
async def create_venue(
    venue_in: VenueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    if current_user.role not in ["admin", "venue_owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only verified turf arena owners or platform admins can register new venues."
        )
        
    db_venue = Venue.model_validate(venue_in)
    db_venue.location = f"POINT({venue_in.lng} {venue_in.lat})"
    db.add(db_venue)
    await db.commit()
    await db.refresh(db_venue)
    return db_venue

@router.get("", response_model=List[VenueRead])
async def list_venues(
    city: Optional[str] = None,
    sport: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    statement = select(Venue)
    
    if city:
        if city in ["Bangalore", "Bengaluru"]:
            statement = statement.where(Venue.city.in_(["Bangalore", "Bengaluru"]))
        else:
            statement = statement.where(Venue.city == city)
    if sport:
        statement = statement.where(sport == any_(Venue.sports))
        
    statement = statement.offset(offset).limit(limit)
    result = await db.execute(statement)
    venues = result.scalars().all()
    return venues

@router.get("/{id}", response_model=VenueRead)
async def get_venue(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    db_venue = await db.get(Venue, id)
    if not db_venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found"
        )
    return db_venue

@router.put("/{id}", response_model=VenueRead)
async def update_venue(
    id: uuid.UUID,
    venue_in: VenueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    db_venue = await db.get(Venue, id)
    if not db_venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found"
        )
        
    update_data = venue_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_venue, key, value)
        
    if "lat" in update_data or "lng" in update_data:
        db_venue.location = f"POINT({db_venue.lng} {db_venue.lat})"
        
    db.add(db_venue)
    await db.commit()
    await db.refresh(db_venue)
    return db_venue

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venue(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    db_venue = await db.get(Venue, id)
    if not db_venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found"
        )
    await db.delete(db_venue)
    await db.commit()
    return None

@router.get("/{id}/games", response_model=List[GameRead])
async def list_games_at_venue(
    id: uuid.UUID,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    db_venue = await db.get(Venue, id)
    if not db_venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found"
        )
        
    statement = select(Game).where(Game.venue_id == id).options(selectinload(Game.players))
    statement = statement.offset(offset).limit(limit)
    result = await db.execute(statement)
    games = result.scalars().all()
    return games
