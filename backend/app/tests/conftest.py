"""Shared test fixtures — isolated test database.

Tests run against a separate `fpa_copilot_test` database so they never
touch the dev database. A session-scoped fixture creates tables and seeds
data; each test gets its own session that rolls back on teardown.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.models.base import Base

# Derive test DB URL from the main one: replace database name with fpa_copilot_test
_main_url = settings.database_url
TEST_DATABASE_URL = _main_url.rsplit("/", 1)[0] + "/fpa_copilot_test"


async def _ensure_test_database_exists() -> None:
    """Create the fpa_copilot_test database if it doesn't exist."""
    admin_url = _main_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'fpa_copilot_test'")
        )
        if not result.scalar():
            await conn.execute(text("CREATE DATABASE fpa_copilot_test"))
    await admin_engine.dispose()


async def _seed_test_data() -> None:
    """Seed the test database with company data and simulate 6 months.

    Uses its own engine + session, disposed after seeding, so the
    connection pool is clean for the per-test sessions.
    """
    from app.seed.company_generator import generate_company
    from app.seed.monthly_simulator import simulate_month
    from app.services.forecast_engine import generate_forecast
    from app.services.variance_calculator import calculate_variances

    seed_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    seed_factory = async_sessionmaker(seed_engine, expire_on_commit=False)

    async with seed_factory() as session:
        await generate_company(session)
        await generate_forecast(session)
        for month in range(1, 7):
            period = f"2026-{month:02d}"
            await simulate_month(session, period)
            await calculate_variances(session, period)

    await seed_engine.dispose()


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create tables and seed data once for the entire test session."""
    await _ensure_test_database_exists()

    setup_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with setup_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await setup_engine.dispose()

    await _seed_test_data()

    yield


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session against the isolated test database.

    Each test gets a fresh engine connection so there are no
    'operation in progress' conflicts from previous tests.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()
