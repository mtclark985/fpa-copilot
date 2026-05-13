"""CLI script: wipe and reseed the demo company."""

import asyncio
import sys
from pathlib import Path

# Add backend to path so app imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.base import Base
from app.seed.company_generator import generate_company


async def main() -> None:
    """Wipe all tables and reseed with fresh demo company."""
    engine = create_async_engine(settings.database_url, echo=False)

    # Drop and recreate all tables for a clean slate
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        counts = await generate_company(session)

    await engine.dispose()

    print(f"Seeded demo company:")
    print(f"  Cost centers: {counts['cost_centers']}")
    print(f"  Employees:    {counts['employees']}")
    print(f"  Open positions: {counts['open_positions']}")


if __name__ == "__main__":
    asyncio.run(main())
