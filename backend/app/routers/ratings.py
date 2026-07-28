import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, Game, Rating, RatingCreate, RatingRead, GameRead

router = APIRouter(prefix="/games", tags=["ratings"])

@router.post("/{id}/complete", response_model=GameRead)
async def complete_game(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    # Fetch game with players eagerly loaded
    statement = select(Game).where(Game.id == id).options(selectinload(Game.players))
    result = await db.execute(statement)
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
        
    # Check if the current user is the host
    if game.host_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can complete this game"
        )
        
    game.status = "completed"
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


@router.post("/{id}/ratings", response_model=RatingRead, status_code=status.HTTP_201_CREATED)
async def create_rating(
    id: uuid.UUID,
    rating_in: RatingCreate,
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
        
    # 2. Verify game status is completed
    if game.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rate players in an incomplete game"
        )
        
    # 3. Verify that rater (current_user) is a player in the game
    rater_is_player = any(p.id == current_user.id for p in game.players)
    if not rater_is_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rater must be a player in the game"
        )
        
    # 4. Verify that the rated user is a player in the game
    rated_is_player = any(p.id == rating_in.rated_id for p in game.players)
    if not rated_is_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rated user must be a player in the game"
        )
        
    # 5. Verify that rater is not rating themselves
    if current_user.id == rating_in.rated_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot rate yourself"
        )
        
    # 6. Check if rating already exists for (rater_id, rated_id, game_id)
    rating_exists_statement = select(Rating).where(
        Rating.rater_id == current_user.id,
        Rating.rated_id == rating_in.rated_id,
        Rating.game_id == id
    )
    rating_exists_result = await db.execute(rating_exists_statement)
    if rating_exists_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already rated this player for this game"
        )
        
    # 7. Create rating
    db_rating = Rating(
        rater_id=current_user.id,
        rated_id=rating_in.rated_id,
        game_id=id,
        score=rating_in.score,
        comment=rating_in.comment
    )
    db.add(db_rating)
    await db.flush() # Flush to make the rating visible to the subsequent aggregation query
    
    # 8. Recalculate karma for the rated user
    # Trade-off Decision: Write-denormalization
    # We query all scores for the rated user and compute the new average.
    # If this is the first rating, the average is the rating score itself.
    scores_statement = select(Rating.score).where(Rating.rated_id == rating_in.rated_id)
    scores_result = await db.execute(scores_statement)
    all_scores = scores_result.scalars().all()
    
    # Calculate average (including the current rating)
    total_score = sum(all_scores)
    count = len(all_scores)
    new_karma = float(total_score) / count if count > 0 else 5.0
    
    # Update user's karma
    rated_user = await db.get(User, rating_in.rated_id)
    if rated_user:
        rated_user.karma = new_karma
        db.add(rated_user)
        
    await db.commit()
    await db.refresh(db_rating)
    
    return db_rating
