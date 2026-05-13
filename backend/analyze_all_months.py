import asyncio
from app.db import async_session_factory
from app.agents.variance_detector import VarianceDetectorAgent

PERIODS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

async def main():
    agent = VarianceDetectorAgent()
    for period in PERIODS:
        print(f"\n=== Analyzing {period} ===")
        async with async_session_factory() as session:
            result = await agent.analyze_period(session, period)
            print(f"  Summary: {result.summary[:150]}...")
            print(f"  Assessments: {len(result.assessments)}")

asyncio.run(main())