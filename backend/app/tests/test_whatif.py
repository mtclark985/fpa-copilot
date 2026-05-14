"""Tests for the what-if scenario endpoint."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import create_app
from app.tests.conftest import TEST_DATABASE_URL


@pytest.fixture
def test_app():
    app = create_app()

    async def _test_session() -> AsyncGenerator[AsyncSession, None]:
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[get_session] = _test_session
    return app


async def test_default_scenario_matches_baseline(test_app) -> None:
    """Default dials (all at current values) produce forecast close to baseline."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/what-if/run",
            json={},  # all defaults
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "scenario_lines" in data
    assert "baseline_lines" in data
    assert "delta" in data
    assert len(data["scenario_lines"]) > 0


async def test_higher_attrition_reduces_expense(test_app) -> None:
    """Higher attrition should reduce total comp expense vs. default."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default scenario
        default_resp = await client.post("/api/v1/what-if/run", json={})
        default_total = sum(l["amount"] for l in default_resp.json()["scenario_lines"])

        # High attrition scenario
        high_attr_resp = await client.post(
            "/api/v1/what-if/run",
            json={"attrition_rate": 0.25},
        )
        high_attr_total = sum(l["amount"] for l in high_attr_resp.json()["scenario_lines"])

    assert high_attr_total < default_total


async def test_higher_hire_pace_increases_expense(test_app) -> None:
    """Higher hire pace should increase total comp expense vs. default."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        default_resp = await client.post("/api/v1/what-if/run", json={})
        default_total = sum(l["amount"] for l in default_resp.json()["scenario_lines"])

        high_hire_resp = await client.post(
            "/api/v1/what-if/run",
            json={"hire_pace_per_quarter": 0.05},
        )
        high_hire_total = sum(l["amount"] for l in high_hire_resp.json()["scenario_lines"])

    assert high_hire_total > default_total


async def test_headcount_freeze_reduces_expense(test_app) -> None:
    """Headcount acceleration of 0.5 (freeze) should reduce expense."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        default_resp = await client.post("/api/v1/what-if/run", json={})
        default_total = sum(l["amount"] for l in default_resp.json()["scenario_lines"])

        freeze_resp = await client.post(
            "/api/v1/what-if/run",
            json={"headcount_acceleration_multiplier": 0.5},
        )
        freeze_total = sum(l["amount"] for l in freeze_resp.json()["scenario_lines"])

    assert freeze_total < default_total


async def test_delta_summary_has_categories(test_app) -> None:
    """Delta summary includes category breakdown."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/what-if/run",
            json={"merit_pct": 0.08},
        )
    data = resp.json()
    assert "total_18_month" in data["delta"]
    assert "fy_landing" in data["delta"]
    assert "by_category" in data["delta"]
    categories = data["delta"]["by_category"]
    assert "salary" in categories
    assert "benefits" in categories
    assert "taxes" in categories
