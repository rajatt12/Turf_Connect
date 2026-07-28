import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, Game, GameCreate, GameRead, Venue

router = APIRouter(prefix="/games", tags=["games"])

@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
async def create_game(
    game_in: GameCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # Validate venue if provided
    if game_in.venue_id:
        venue = await db.get(Venue, game_in.venue_id)
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Venue not found"
            )

    # Validate team if provided
    if game_in.team_id:
        from app.models import Team, TeamMember
        team = await db.get(Team, game_in.team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        # Verify user is a member of the team
        stmt_member = select(TeamMember).where(TeamMember.team_id == game_in.team_id, TeamMember.user_id == current_user.id)
        res_member = await db.execute(stmt_member)
        member = res_member.scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a member of the team to host a game on their behalf"
            )

    # Create the Game instance and auto-join the host as player 1
    db_game = Game(
        host_id=current_user.id,
        sport=game_in.sport,
        city=game_in.city,
        max_players=game_in.max_players,
        venue_id=game_in.venue_id,
        team_id=game_in.team_id,
        status="open",
        players=[current_user]
    )
    db.add(db_game)
    await db.commit()
    
    # Re-query the game with players eagerly loaded to return slots_filled and slots_open correctly
    statement = select(Game).where(Game.id == db_game.id).options(selectinload(Game.players))
    result = await db.execute(statement)
    game = result.scalar_one()
    return game

@router.get("", response_model=List[GameRead])
async def list_games(
    sport: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    team_id: Optional[uuid.UUID] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    # Validate coordinate params grouping
    geo_params = [lat, lng, radius_km]
    if any(p is not None for p in geo_params) and not all(p is not None for p in geo_params):
        raise HTTPException(
            status_code=400,
            detail="If any of lat, lng, or radius_km is provided, all must be provided."
        )

    statement = select(Game).options(selectinload(Game.players))
    
    if sport:
        statement = statement.where(Game.sport == sport)
    if city:
        statement = statement.where(Game.city == city)
    if status:
        statement = statement.where(Game.status == status)
    if team_id:
        statement = statement.where(Game.team_id == team_id)
        
    if lat is not None and lng is not None and radius_km is not None:
        from sqlalchemy import func
        from geoalchemy2 import Geography
        
        ref_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
        
        statement = statement.join(Venue)
        statement = statement.where(
            func.ST_DWithin(Venue.location, func.cast(ref_point, Geography), radius_km * 1000)
        )
        statement = statement.order_by(
            func.ST_Distance(Venue.location, func.cast(ref_point, Geography))
        )
        
    statement = statement.offset(offset).limit(limit)
    result = await db.execute(statement)
    games = result.scalars().all()
    return games

@router.get("/{id}", response_model=GameRead)
async def get_game(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    statement = select(Game).where(Game.id == id).options(selectinload(Game.players))
    result = await db.execute(statement)
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    return game

@router.post("/{id}/join", response_model=GameRead)
async def join_game(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # 1. Fetch the game with players eagerly loaded
    statement = select(Game).where(Game.id == id).options(selectinload(Game.players))
    result = await db.execute(statement)
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
        
    # 2. Check if game is open
    if game.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game is not open"
        )
        
    # 3. Check if user is already joined
    if any(p.id == current_user.id for p in game.players):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already joined this game"
        )
        
    # 4. Add user to players list
    game.players.append(current_user)
    
    # 5. Check if the game is now full
    if len(game.players) >= game.max_players:
        game.status = "full"
        
    db.add(game)
    await db.commit()
    await db.refresh(game)
    
    # Notify host that player joined (if joiner is not host)
    if current_user.id != game.host_id:
        from app.core.queue import enqueue_task
        await enqueue_task(
            "send_notification",
            str(game.host_id),
            "Player Joined",
            f"{current_user.name} has joined your game of {game.sport}.",
            "join"
        )
        
    return game
