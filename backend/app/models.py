import uuid
import datetime
from typing import Optional, List, Any
from fastapi_users import schemas
from sqlmodel import SQLModel, Field, Relationship, Column, String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from geoalchemy2 import Geography

# ==========================================
# 1. Database Association & Models
# ==========================================
class GamePlayer(SQLModel, table=True):
    __tablename__ = "game_player"
    game_id: uuid.UUID = Field(foreign_key="game.id", primary_key=True, nullable=False)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, nullable=False)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    email: str = Field(
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)
    
    # Custom profile fields
    name: str = Field(nullable=False)
    skill_level: str = Field(nullable=False) # e.g. "Beginner", "Intermediate", "Advanced"
    city: str = Field(nullable=False)
    role: str = Field(default="player", nullable=False) # e.g. "player", "admin"
    karma: float = Field(default=5.0, nullable=False)

    # Relationships
    games: list["Game"] = Relationship(back_populates="players", link_model=GamePlayer)
    bookings: list["Booking"] = Relationship(back_populates="user")
    team_memberships: list["TeamMember"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class Venue(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    name: str = Field(nullable=False)
    address: str = Field(nullable=False)
    city: str = Field(nullable=False)
    sports: list[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
    hourly_rate: float = Field(nullable=False)
    opening_time: datetime.time = Field(nullable=False)
    closing_time: datetime.time = Field(nullable=False)
    lat: float = Field(nullable=False)
    lng: float = Field(nullable=False)
    location: Optional[str] = Field(default=None, nullable=True)

    # Relationships
    games: list["Game"] = Relationship(back_populates="venue")
    bookings: list["Booking"] = Relationship(back_populates="venue")


class Game(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    host_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    venue_id: Optional[uuid.UUID] = Field(default=None, foreign_key="venue.id", nullable=True)
    sport: str = Field(nullable=False)
    city: str = Field(nullable=False)
    status: str = Field(default="open", nullable=False) # e.g. "open", "full"
    max_players: int = Field(nullable=False)
    starts_at: Optional[datetime.datetime] = Field(default=None, nullable=True)
    skill_level: Optional[str] = Field(default="All Levels", nullable=True)

    team_id: Optional[uuid.UUID] = Field(default=None, foreign_key="team.id", nullable=True)

    # Relationships
    players: list["User"] = Relationship(back_populates="games", link_model=GamePlayer)
    venue: Optional[Venue] = Relationship(back_populates="games")
    messages: list["Message"] = Relationship(back_populates="game")
    team: Optional["Team"] = Relationship(back_populates="games")

    # Computed fields (properties)
    @property
    def slots_filled(self) -> int:
        return len(self.players) if self.players is not None else 0

    @property
    def slots_open(self) -> int:
        return self.max_players - self.slots_filled


class Booking(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    venue_id: uuid.UUID = Field(foreign_key="venue.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    starts_at: datetime.datetime = Field(nullable=False)
    ends_at: datetime.datetime = Field(nullable=False)
    status: str = Field(default="unpaid", nullable=False) # "unpaid", "paid", "cancelled"

    # Relationships
    venue: Optional[Venue] = Relationship(back_populates="bookings")
    user: Optional[User] = Relationship(back_populates="bookings")
    payments: list["Payment"] = Relationship(back_populates="booking")


class Payment(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    booking_id: uuid.UUID = Field(foreign_key="booking.id", nullable=False)
    amount: float = Field(nullable=False)
    currency: str = Field(default="INR", nullable=False)
    gateway_order_id: str = Field(nullable=False, index=True)
    gateway_payment_id: Optional[str] = Field(default=None, nullable=True)
    status: str = Field(default="pending", nullable=False) # "pending", "successful", "failed"

    # Relationships
    booking: Optional[Booking] = Relationship(back_populates="payments")


class Message(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    game_id: uuid.UUID = Field(foreign_key="game.id", nullable=False)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    body: str = Field(nullable=False)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False
    )

    # Relationships
    game: Optional[Game] = Relationship(back_populates="messages")
    user: Optional[User] = Relationship()


class Rating(SQLModel, table=True):
    __tablename__ = "rating"
    __table_args__ = (
        UniqueConstraint("rater_id", "rated_id", "game_id", name="uq_rating_rater_rated_game"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    rater_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    rated_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    game_id: uuid.UUID = Field(foreign_key="game.id", nullable=False)
    score: int = Field(nullable=False)
    comment: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False
    )


class Notification(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, nullable=False)
    title: str = Field(nullable=False)
    body: str = Field(nullable=False)
    type: str = Field(nullable=False)
    read: bool = Field(default=False, nullable=False)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False
    )

    user: Optional[User] = Relationship()


class DeviceToken(SQLModel, table=True):
    __tablename__ = "device_token"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, nullable=False)
    token: str = Field(nullable=False, unique=True, index=True)
    platform: str = Field(nullable=False)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False
    )

    user: Optional[User] = Relationship()


class Team(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False
    )
    name: str = Field(nullable=False, unique=True, index=True)
    description: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False
    )

    # Relationships
    memberships: list["TeamMember"] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    games: list["Game"] = Relationship(back_populates="team")


class TeamMember(SQLModel, table=True):
    __tablename__ = "team_member"
    team_id: uuid.UUID = Field(foreign_key="team.id", primary_key=True, nullable=False)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, nullable=False)
    role: str = Field(default="member", nullable=False)

    # Relationships
    team: "Team" = Relationship(back_populates="memberships")
    user: "User" = Relationship(back_populates="team_memberships")


class Follow(SQLModel, table=True):
    __tablename__ = "follow"
    follower_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, nullable=False)
    followee_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True, nullable=False)



# ==========================================
# 2. Pydantic schemas for FastAPI-Users CRUD
# ==========================================
class UserRead(schemas.BaseUser[uuid.UUID]):
    name: str
    skill_level: str
    city: str
    role: str
    karma: float


class UserCreate(schemas.BaseUserCreate):
    name: str
    skill_level: str
    city: str


class UserUpdate(schemas.BaseUserUpdate):
    name: Optional[str] = None
    skill_level: Optional[str] = None
    city: Optional[str] = None
    role: Optional[str] = None


# ==========================================
# 3. Pydantic schemas for Games
# ==========================================
class GameCreate(SQLModel):
    sport: str
    city: str
    max_players: int
    starts_at: Optional[datetime.datetime] = None
    skill_level: Optional[str] = "All Levels"
    venue_id: Optional[uuid.UUID] = None
    team_id: Optional[uuid.UUID] = None


class GameRead(GameCreate):
    id: uuid.UUID
    host_id: uuid.UUID
    status: str
    slots_filled: int
    slots_open: int
    starts_at: Optional[datetime.datetime] = None
    skill_level: Optional[str] = "All Levels"
    team_id: Optional[uuid.UUID] = None
    players: list["UserRead"] = []


# ==========================================
# 4. Pydantic schemas for Venues
# ==========================================
class VenueCreate(SQLModel):
    name: str
    address: str
    city: str
    sports: list[str]
    hourly_rate: float
    opening_time: datetime.time
    closing_time: datetime.time
    lat: float
    lng: float


class VenueUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    sports: Optional[list[str]] = None
    hourly_rate: Optional[float] = None
    opening_time: Optional[datetime.time] = None
    closing_time: Optional[datetime.time] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class VenueRead(VenueCreate):
    id: uuid.UUID


# ==========================================
# 5. Pydantic schemas for Bookings
# ==========================================
class BookingCreate(SQLModel):
    venue_id: uuid.UUID
    starts_at: datetime.datetime
    ends_at: datetime.datetime


class BookingRead(BookingCreate):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str


# ==========================================
# 6. Pydantic schemas for Payments
# ==========================================
class PaymentRead(SQLModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: float
    currency: str
    gateway_order_id: str
    gateway_payment_id: Optional[str] = None
    status: str


# ==========================================
# 7. Pydantic schemas for Chat Messages
# ==========================================
class MessageRead(SQLModel):
    id: uuid.UUID
    game_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    body: str
    created_at: datetime.datetime


# ==========================================
# 8. Pydantic schemas for Ratings
# ==========================================
class RatingCreate(SQLModel):
    rated_id: uuid.UUID
    score: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class RatingRead(SQLModel):
    id: uuid.UUID
    rater_id: uuid.UUID
    rated_id: uuid.UUID
    game_id: uuid.UUID
    score: int
    comment: Optional[str]
    created_at: datetime.datetime


# ==========================================
# 9. Pydantic schemas for Notifications
# ==========================================
class DeviceTokenCreate(SQLModel):
    token: str
    platform: str


class DeviceTokenRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    token: str
    platform: str
    created_at: datetime.datetime


class NotificationRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    body: str
    type: str
    read: bool
    created_at: datetime.datetime


# ==========================================
# 10. Pydantic schemas for Teams
# ==========================================
class TeamCreate(SQLModel):
    name: str
    description: Optional[str] = None


class TeamRead(SQLModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime.datetime


class TeamMemberRead(SQLModel):
    user_id: uuid.UUID
    name: str
    role: str


class TeamDetailedRead(TeamRead):
    members: list[TeamMemberRead]


class RoleUpdate(SQLModel):
    role: str
