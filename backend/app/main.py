from contextlib import asynccontextmanager
import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import redis.asyncio as redis

from app.core.config import settings
from app.core.db import get_db, async_session_maker
from app.core.users import fastapi_users, auth_backend, UserManager
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from app.models import User, UserRead, UserCreate, UserUpdate
from app.routers.games import router as games_router
from app.routers.venues import router as venues_router
from app.routers.bookings import router as bookings_router
from app.routers.payments import router as payments_router
from app.routers.chat import router as chat_router
from app.routers.ratings import router as ratings_router
from app.routers.notifications import router as notifications_router
from app.routers.teams import router as teams_router
from app.routers.social import router as social_router

# ==========================================
# 1. Lifespan / Startup Seeding Logic
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlmodel import SQLModel
    from app.core.db import engine
    import app.models as models
    from app.models import Venue

    # 1. Create all tables on startup if not already created
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("Database schema verified and tables created successfully.")
    except Exception as e:
        print(f"Table creation check warning: {e}")

    # 2. Seed Developer Admin & Athletes & Venues if empty
    async with async_session_maker() as session:
        try:
            result = await session.execute(select(User).where(User.email == "dev@example.com"))
            dev_user = result.scalars().first()
            if not dev_user:
                print("Seeding developer user...")
                user_db = SQLAlchemyUserDatabase(session, User)
                user_manager = UserManager(user_db)
                
                dev_create = UserCreate(
                    email="dev@example.com",
                    password="devpassword123",
                    name="Dev User",
                    skill_level="Advanced",
                    city="Mumbai"
                )
                created_dev = await user_manager.create(dev_create, safe=False)
                created_dev.role = "admin"
                session.add(created_dev)
                await session.commit()
                print("Developer admin seeded!")

            # Seed Athletes
            athlete_seeds = [
                {"name": "Dhruv Beotra", "email": "dhruv@example.com", "skill_level": "Advanced", "city": "Bangalore", "karma": 5.0},
                {"name": "Alex Kumar", "email": "alex@example.com", "skill_level": "Intermediate", "city": "Mumbai", "karma": 4.9},
                {"name": "Ananya Sharma", "email": "ananya@example.com", "skill_level": "Advanced", "city": "Bangalore", "karma": 5.0},
                {"name": "Vikram Rathore", "email": "vikram@example.com", "skill_level": "Intermediate", "city": "Delhi", "karma": 4.8},
                {"name": "Karan Patel", "email": "karan@example.com", "skill_level": "Beginner", "city": "Pune", "karma": 5.0}
            ]
            user_db = SQLAlchemyUserDatabase(session, User)
            user_manager = UserManager(user_db)
            for a in athlete_seeds:
                res = await session.execute(select(User).where(User.email == a["email"]))
                if not res.scalars().first():
                    u_in = UserCreate(
                        email=a["email"],
                        password="password123",
                        name=a["name"],
                        skill_level=a["skill_level"],
                        city=a["city"]
                    )
                    created_a = await user_manager.create(u_in, safe=False)
                    created_a.karma = a["karma"]
                    session.add(created_a)
            await session.commit()

            # Seed Venues
            venue_res = await session.execute(select(Venue))
            if not venue_res.scalars().first():
                sample_venues = [
                    Venue(
                        name="Novex Padel & Turf Arena",
                        address="Andheri Sports Complex, Link Road",
                        city="Mumbai",
                        sports=["Tennis", "Padel", "Football"],
                        hourly_rate=1500.0,
                        opening_time=datetime.time(6, 0),
                        closing_time=datetime.time(23, 0),
                        lat=19.1136,
                        lng=72.8697
                    ),
                    Venue(
                        name="Playfield Champions Arena",
                        address="Koramangala 4th Block",
                        city="Bangalore",
                        sports=["Football", "Cricket", "Badminton"],
                        hourly_rate=1200.0,
                        opening_time=datetime.time(6, 0),
                        closing_time=datetime.time(23, 0),
                        lat=12.9352,
                        lng=77.6245
                    ),
                    Venue(
                        name="MatchPoint Box Turf Hub",
                        address="Hauz Khas Enclave",
                        city="Delhi",
                        sports=["Cricket", "Football", "Basketball"],
                        hourly_rate=1400.0,
                        opening_time=datetime.time(6, 0),
                        closing_time=datetime.time(23, 0),
                        lat=28.5494,
                        lng=77.2001
                    ),
                    Venue(
                        name="Greenfield Sports Hub",
                        address="Kalyani Nagar",
                        city="Pune",
                        sports=["Football", "Badminton"],
                        hourly_rate=1000.0,
                        opening_time=datetime.time(6, 0),
                        closing_time=datetime.time(23, 0),
                        lat=18.5463,
                        lng=73.9033
                    )
                ]
                for v in sample_venues:
                    session.add(v)
                await session.commit()
                print("Sample venues seeded successfully!")

        except Exception as e:
            print(f"Startup seeding error: {e}")
            
    # Start the Redis tasks queue worker if available
    try:
        from app.core.queue import start_worker, stop_worker
        start_worker()
        print("Background task queue worker started.")
    except Exception as e:
        print(f"Task queue worker initialization skipped: {e}")
            
    yield
    
    # Shutdown queue worker
    try:
        await stop_worker()
        print("Background task queue worker stopped.")
    except Exception:
        pass

# ==========================================
# 2. FastAPI Application Setup
# ==========================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend service for Turf - Game finder web app",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration to allow local & cloud frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_origin_regex=r"https://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. Mount fastapi-users Routers
# ==========================================
# Authentication routes (login / logout)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)

# Registration route
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"]
)

# User profile management route
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"]
)

# Games routes
app.include_router(games_router)

# Venues routes
app.include_router(venues_router)

# Bookings routes
app.include_router(bookings_router)

# Payments routes
app.include_router(payments_router)

# Chat routes (WebSocket)
app.include_router(chat_router)

# Ratings routes
app.include_router(ratings_router)

# Notifications routes
app.include_router(notifications_router)

# Teams routes
app.include_router(teams_router)

# Social routes
app.include_router(social_router)

# ==========================================
# 4. Core Endpoints (Health check)
# ==========================================
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unhealthy"
    redis_status = "unhealthy"
    
    # 1. Check Database connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    # 2. Check Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose() # Close connection explicitly
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
        
    # Return 503 if any service is down
    if db_status != "healthy" or redis_status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": db_status,
                "redis": redis_status
            }
        )
        
    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status
    }
