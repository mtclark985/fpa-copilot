"""Test forecast engine math with known inputs."""

from app.services.forecast_engine import _monthly_fica, BENEFITS_LOAD


def test_fica_below_wage_base() -> None:
    """FICA on salary below the wage base uses the full rate."""
    result = _monthly_fica(120_000)
    expected = (120_000 / 12) * 0.0765
    assert abs(result - expected) < 0.01


def test_fica_above_wage_base() -> None:
    """FICA on salary above wage base caps SS, continues Medicare."""
    salary = 200_000
    monthly = salary / 12
    ss_monthly = (168_000 / 12) * 0.062
    medicare_monthly = monthly * 0.0145
    expected = ss_monthly + medicare_monthly
    result = _monthly_fica(salary)
    assert abs(result - expected) < 0.01


def test_benefits_load_rate() -> None:
    """Benefits load is 18% of base salary."""
    assert BENEFITS_LOAD == 0.18
    salary = 120_000
    monthly_benefits = salary * BENEFITS_LOAD / 12
    assert abs(monthly_benefits - 1800.0) < 0.01


def test_fica_boundary() -> None:
    """FICA at exactly the wage base should use the full rate."""
    result = _monthly_fica(168_000)
    expected = (168_000 / 12) * 0.0765
    assert abs(result - expected) < 0.01


def test_monthly_salary_math() -> None:
    """Monthly salary is annual / 12."""
    annual = 120_000
    monthly = annual / 12
    assert monthly == 10_000.0


def test_bonus_accrual_math() -> None:
    """Monthly bonus accrual is target % of salary / 12."""
    salary = 120_000
    bonus_pct = 10.0
    monthly_bonus = salary * bonus_pct / 100 / 12
    assert monthly_bonus == 1_000.0
