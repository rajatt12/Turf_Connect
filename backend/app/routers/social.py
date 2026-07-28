import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import User, UserRead, Follow, Game, GameRead

router = APIRouter(prefix="/users", tags=["social"])


@router.post("/{id}/follow", status_code=status.HTTP_200_OK)
async def follow_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Verify target user exists
    target_user = await db.get(User, id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Cannot follow yourself
    if id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )

    # Check if already following
    stmt = select(Follow).where(
        Follow.follower_id == current_user.id, Follow.followee_id == id
    )
    res = await db.execute(stmt)
    existing_follow = res.scalar_one_or_none()
    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user",
        )

    # Create Follow
    new_follow = Follow(follower_id=current_user.id, followee_id=id)
    db.add(new_follow)
    await db.commit()

    return {"message": "Followed user successfully"}


@router.post("/{id}/unfollow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Verify target user exists
    target_user = await db.get(User, id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if following
    stmt = select(Follow).where(
        Follow.follower_id == current_user.id, Follow.followee_id == id
    )
    res = await db.execute(stmt)
    existing_follow = res.scalar_one_or_none()
    if not existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not following this user",
        )

    # Delete Follow
    await db.delete(existing_follow)
    await db.commit()

    return {"message": "Unfollowed user successfully"}


@router.get("/{id}/following", response_model=List[UserRead])
async def list_following(
    id: uuid.UUID,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    # Verify target user exists
    target_user = await db.get(User, id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = (
        select(User)
        .join(Follow, User.id == Follow.followee_id)
        .where(Follow.follower_id == id)
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    following_users = res.scalars().all()
    return following_users


@router.get("/{id}/followers", response_model=List[UserRead])
async def list_followers(
    id: uuid.UUID,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    # Verify target user exists
    target_user = await db.get(User, id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    stmt = (
        select(User)
        .join(Follow, User.id == Follow.follower_id)
        .where(Follow.followee_id == id)
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    follower_users = res.scalars().all()
    return follower_users


@router.get("/me/feed", response_model=List[GameRead])
async def get_feed(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Retrieve all followee IDs
    stmt_followees = select(Follow.followee_id).where(
        Follow.follower_id == current_user.id
    )
    res_followees = await db.execute(stmt_followees)
    followee_ids = res_followees.scalars().all()

    if not followee_ids:
        return []

    # Query games hosted by those users
    stmt_games = (
        select(Game)
        .where(Game.host_id.in_(followee_ids))
        .options(selectinload(Game.players))
        .offset(offset)
        .limit(limit)
    )
    res_games = await db.execute(stmt_games)
    games = res_games.scalars().all()
    return games
