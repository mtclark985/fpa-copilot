"""One-shot demo setup: seed company, generate forecast, simulate 6 months, calculate variances."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.base import Base
from app.seed.company_generator import generate_company
from app.services.forecast_engine import generate_forecast
from app.seed.monthly_simulator import simulate_month
from app.services.variance_calculator import calculate_variances


async def main() -> None:
    """Full demo setup: wipe, seed, forecast, simulate 6 months."""
    engine = create_async_engine(settings.database_url, echo=False)

    print("1/4  Resetting database...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    print("2/4  Seeding demo company...")
    async with factory() as session:
        counts = await generate_company(session)
    print(f"     {counts['employees']} employees, {counts['cost_centers']} cost centers, {counts['open_positions']} open positions")

    print("3/4  Generating forecast...")
    async with factory() as session:
        version = await generate_forecast(session)
    print(f"     Created: {version.name}")

    print("4/4  Simulating 6 months of actuals...")
    for m in range(1, 7):
        period = f"2026-{m:02d}"
        async with factory() as session:
            summary = await simulate_month(session, period)
        async with factory() as session:
            variances = await calculate_variances(session, period)
        print(f"     {period}: {summary['story']} ({len(variances)} variances)")

    await engine.dispose()
    print("\nDemo setup complete! Start the backend and frontend to explore.")


if __name__ == "__main__":
    asyncio.run(main())
