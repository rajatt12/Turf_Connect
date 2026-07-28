import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.core.db import get_db
from app.core.users import current_active_user
from app.models import (
    User,
    Team,
    TeamMember,
    TeamCreate,
    TeamRead,
    TeamDetailedRead,
    TeamMemberRead,
    RoleUpdate,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_in: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Check if name already taken
    stmt = select(Team).where(Team.name == team_in.name)
    res = await db.execute(stmt)
    existing_team = res.scalar_one_or_none()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name already taken",
        )

    # Create team
    db_team = Team(name=team_in.name, description=team_in.description)
    db.add(db_team)
    await db.flush()  # populate team.id

    # Create team member (captain)
    db_member = TeamMember(
        team_id=db_team.id, user_id=current_user.id, role="captain"
    )
    db.add(db_member)

    await db.commit()
    await db.refresh(db_team)
    return db_team


@router.get("", response_model=List[TeamRead])
async def list_teams(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Team).offset(offset).limit(limit)
    res = await db.execute(stmt)
    teams = res.scalars().all()
    return teams


@router.get("/{id}", response_model=TeamDetailedRead)
async def get_team(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # Retrieve the team
    db_team = await db.get(Team, id)
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Fetch members of the team with User info (name)
    stmt = (
        select(TeamMember, User)
        .join(User, TeamMember.user_id == User.id)
        .where(TeamMember.team_id == id)
    )
    res = await db.execute(stmt)

    members_list = []
    for team_member, user in res:
        members_list.append(
            TeamMemberRead(
                user_id=user.id,
                name=user.name,
                role=team_member.role,
            )
        )

    return TeamDetailedRead(
        id=db_team.id,
        name=db_team.name,
        description=db_team.description,
        created_at=db_team.created_at,
        members=members_list,
    )


@router.post("/{id}/join", status_code=status.HTTP_200_OK)
async def join_team(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Verify team exists
    db_team = await db.get(Team, id)
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Check if already a member
    stmt = select(TeamMember).where(
        TeamMember.team_id == id, TeamMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    existing_member = res.scalar_one_or_none()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this team",
        )

    # Add member
    db_member = TeamMember(team_id=id, user_id=current_user.id, role="member")
    db.add(db_member)
    await db.commit()

    return {"message": "Joined team successfully"}


@router.post("/{id}/leave", status_code=status.HTTP_200_OK)
async def leave_team(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Verify team exists
    db_team = await db.get(Team, id)
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Get team member record
    stmt = select(TeamMember).where(
        TeamMember.team_id == id, TeamMember.user_id == current_user.id
    )
    res = await db.execute(stmt)
    db_member = res.scalar_one_or_none()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a member of this team",
        )

    if db_member.role == "captain":
        # Check total number of members in the team
        stmt_count = select(func.count(TeamMember.user_id)).where(
            TeamMember.team_id == id
        )
        res_count = await db.execute(stmt_count)
        member_count = res_count.scalar()

        if member_count > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Captain cannot leave the team without transferring captaincy first.",
            )
        else:
            # If captain is the only member, delete the team
            await db.delete(db_team)
    else:
        # Regular member leaves
        await db.delete(db_member)

    await db.commit()
    return {"message": "Left team successfully"}


@router.post("/{id}/members/{user_id}/role", status_code=status.HTTP_200_OK)
async def update_member_role(
    id: uuid.UUID,
    user_id: uuid.UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    # Verify role input is valid
    if role_in.role not in ["captain", "member"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'captain' or 'member'",
        )

    # Verify team exists
    db_team = await db.get(Team, id)
    if not db_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Verify calling user is the captain
    stmt_caller = select(TeamMember).where(
        TeamMember.team_id == id, TeamMember.user_id == current_user.id
    )
    res_caller = await db.execute(stmt_caller)
    db_caller = res_caller.scalar_one_or_none()
    if not db_caller or db_caller.role != "captain":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the captain can modify member roles",
        )

    # Verify target user is a member of the team
    stmt_target = select(TeamMember).where(
        TeamMember.team_id == id, TeamMember.user_id == user_id
    )
    res_target = await db.execute(stmt_target)
    db_target = res_target.scalar_one_or_none()
    if not db_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this team",
        )

    # Cannot update own role directly
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role directly. Transfer captaincy to another member instead.",
        )

    # Perform role change
    if role_in.role == "captain":
        # Transfer captaincy: target becomes captain, caller becomes member
        db_target.role = "captain"
        db_caller.role = "member"
        db.add(db_target)
        db.add(db_caller)
    else:
        # Demote target to member (usually target is already a member, but supported)
        db_target.role = "member"
        db.add(db_target)

    await db.commit()
    return {"message": "Role updated successfully"}
