import asyncio
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.main import app
from app.core.config import settings
from app.core.db import get_db

@pytest.fixture
async def test_engine():
    """Create database engine and tables for the duration of a test."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    
    # Create tables fresh for this test
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    yield engine
    
    # Clean up and drop tables after this test
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(autouse=True)
async def clean_redis():
    import redis.asyncio as redis
    r = redis.from_url(settings.REDIS_URL)
    await r.delete("turf_tasks_queue")
    # Reset retry tracking
    from app.core.queue import retry_counts
    retry_counts.clear()
    await r.aclose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for a single test."""
    async_session = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        # No explicit transaction begin/rollback here; test isolation is handled
        # by creating and dropping the tables in the test_engine fixture.

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client pointing to the FastAPI app with an overridden DB dependency."""
    async def _get_test_db():
        yield db_session
        
    app.dependency_overrides[get_db] = _get_test_db
    
    # Explicitly run app lifespan context manager to guarantee background tasks start/stop
    async with app.router.lifespan_context(app):
        import httpx
        # Use AsyncClient to hit the application
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
        
    app.dependency_overrides.clear()


@pytest.fixture
def mock_razorpay():
    with patch("razorpay.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock order creation
        mock_order = MagicMock()
        mock_order.create.return_value = {"id": "order_test123"}
        mock_client.order = mock_order
        
        # Mock signature verification (does nothing = successful)
        mock_utility = MagicMock()
        mock_client.utility = mock_utility
        
        yield mock_client
