"""
Shared test fixtures for the backend test suite.

Provides an in-memory SQLite database and a TestClient that uses it,
so tests run fast and don't need a PostgreSQL instance.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app as application
import app.models  # noqa: F401 — register all models

import logging
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ── In-memory async engine for tests ────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Enable SQLite foreign key enforcement (disabled by default)
from sqlalchemy import event  # noqa: E402

@event.listens_for(test_engine.sync_engine, "connect")
def _enable_sqlite_fks(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Ensure app.db.session and settings point to the in-memory test database and offline fixtures
import app.db.session
from app.core.config import settings

app.db.session.engine = test_engine
app.db.session.async_session_factory = TestSessionFactory
settings.database_url = TEST_DATABASE_URL
settings.google_factcheck_api_key = None
settings.model_load_on_startup = False

from app.ml.model_registry import registry
registry.unload()


async def override_get_session():
    """Yield a test session instead of the real database session."""
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Override the dependency for all tests
application.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def _setup_db():
    """Create tables before each test and drop them after."""
    import asyncio

    async def _create():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_create())
    yield
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_drop())


@pytest.fixture
def client() -> TestClient:
    """Provide a synchronous test client for the FastAPI app."""
    return TestClient(application)


@pytest.fixture
def async_session():
    """Provide a raw async session for direct repository tests."""
    return TestSessionFactory
