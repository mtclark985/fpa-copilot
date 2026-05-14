"""Tests for the transparency API endpoints."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_session
from app.main import create_app
from app.tests.conftest import TEST_DATABASE_URL


def _make_test_app():
    """Create a test app with DB dependency pointing to the test database."""
    test_app = create_app()

    async def _test_session() -> AsyncGenerator[AsyncSession, None]:
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            yield session
        await engine.dispose()

    test_app.dependency_overrides[get_session] = _test_session
    return test_app


@pytest.fixture
def test_app():
    return _make_test_app()


async def test_employees_endpoint(test_app) -> None:
    """Transparency employees endpoint returns paginated results."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transparency/employees")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "employees" in data
    assert data["total"] > 0
    assert len(data["employees"]) > 0
    emp = data["employees"][0]
    assert "employee_number" in emp
    assert "cost_center_name" in emp
    assert "status" in emp


async def test_employees_search_filter(test_app) -> None:
    """Employee search filters by name or employee_number."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transparency/employees?search=E0001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_employees_status_filter(test_app) -> None:
    """Employee status filter works."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transparency/employees?status=active")
    assert resp.status_code == 200
    data = resp.json()
    for emp in data["employees"]:
        assert emp["status"] == "active"


async def test_hiring_plan_endpoint(test_app) -> None:
    """Hiring plan endpoint returns open positions and recent hires."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transparency/hiring-plan")
    assert resp.status_code == 200
    data = resp.json()
    assert "open_positions" in data
    assert "recent_hires" in data
    assert isinstance(data["open_positions"], list)
    assert isinstance(data["recent_hires"], list)


async def test_assumptions_endpoint(test_app) -> None:
    """Assumptions endpoint returns structured assumption metadata."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transparency/assumptions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    categories = {item["category"] for item in data}
    assert "merit" in categories
    assert "attrition" in categories
    assert "benefits" in categories
    assert "payroll_tax" in categories
    assert "bonus" in categories
    assert "hire_pace" in categories

    for category_group in data:
        assert "name" in category_group
        assert "items" in category_group
        for item in category_group["items"]:
            assert "label" in item
            assert "value" in item
            assert "description" in item
            assert "used_in" in item


async def test_simulator_events_endpoint(test_app) -> None:
    """Simulator events endpoint returns chronological story variances."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/transparency/simulator-events")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6

    periods = [e["period"] for e in data]
    assert periods == sorted(periods)

    for event in data:
        assert "period" in event
        assert "event_type" in event
        assert "narrative" in event
        assert len(event["narrative"]) > 0
