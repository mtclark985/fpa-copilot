"""CLI script: advance the simulation by one month."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.actual import Actual
from app.seed.monthly_simulator import simulate_month


async def main() -> None:
    """Determine the next month and simulate it."""
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        # Find the latest period with actuals
        result = await session.execute(
            select(func.max(Actual.period))
        )
        latest = result.scalar()

        if latest is None:
            next_period = "2026-01"
        else:
            year, month = int(latest[:4]), int(latest[5:7])
            if month == 12:
                next_period = f"{year + 1:04d}-01"
            else:
                next_period = f"{year:04d}-{month + 1:02d}"

        print(f"Simulating month: {next_period}")
        summary = await simulate_month(session, next_period)
        print(f"  Story: {summary['story']}")
        print(f"  Events: {summary['events']}")
        print(f"  Actuals created: {summary['actuals_created']}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
