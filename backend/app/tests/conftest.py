"""Shared test fixtures — uses the real Postgres database.

Model/unit tests use a transactional session that rolls back.
Integration tests (seed, simulator, variance) read the seeded data directly.
"""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

TEST_DATABASE_URL = settings.database_url


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session for reading seeded data.

    Tests that only read data work fine. Tests that write should use
    unique keys to avoid conflicts with seed data.
    """
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with factory() as session:
        yield session
        await session.rollback()

    await test_engine.dispose()
