import asyncio
import traceback
from app.db import async_session_factory
from app.agents.variance_detector import VarianceDetectorAgent

async def main():
    agent = VarianceDetectorAgent()
    print(f"Configured model: {agent.model}")
    print()

    async with async_session_factory() as session:
        try:
            output = await agent.analyze_period(session, "2026-01")
            print("SUCCESS")
            print(output)
        except Exception:
            print("AGENT FAILED:")
            traceback.print_exc()

asyncio.run(main())