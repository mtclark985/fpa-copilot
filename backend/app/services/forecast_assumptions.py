"""Single source of truth for forecast assumptions.

Both forecast_engine.py and the transparency API reference this module.
Changing a value here changes the forecast behavior and what's shown
on the Data & Assumptions page.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastAssumptions:
    """All forecast assumption parameters."""

    # Payroll taxes
    fica_wage_base: float = 168_000
    fica_rate: float = 0.0765  # 6.2% SS + 1.45% Medicare (employer portion)
    medicare_only_rate: float = 0.0145  # Medicare on earnings above FICA wage base

    # Benefits
    benefits_load_pct: float = 0.18  # 18% of base salary

    # Attrition
    annual_attrition_rate: float = 0.12  # 12% annual

    # Merit cycle
    merit_month: int = 4  # April
    merit_avg_pct: float = 0.04  # 4% average merit increase

    # Planned hire pace
    quarterly_hire_growth: float = 0.02  # 2% of headcount per quarter as new hires


# Default assumptions used by the forecast engine
DEFAULT_ASSUMPTIONS = ForecastAssumptions()

# Structured metadata for the transparency API
ASSUMPTIONS_METADATA = [
    {
        "name": "Merit Cycle",
        "category": "merit",
        "items": [
            {
                "name": "merit_avg_pct",
                "label": "Merit Increase",
                "value": DEFAULT_ASSUMPTIONS.merit_avg_pct,
                "unit": "%",
                "display_value": f"{DEFAULT_ASSUMPTIONS.merit_avg_pct * 100:.0f}%",
                "description": "Average annual merit increase applied to all active employees.",
                "used_in": "forecast_engine.py — applied in the merit month to each employee's salary.",
            },
            {
                "name": "merit_month",
                "label": "Merit Month",
                "value": DEFAULT_ASSUMPTIONS.merit_month,
                "unit": "month",
                "display_value": "April (month 4)",
                "description": "The calendar month when the merit cycle is applied.",
                "used_in": "forecast_engine.py — triggers salary adjustments in this month each year.",
            },
        ],
    },
    {
        "name": "Attrition",
        "category": "attrition",
        "items": [
            {
                "name": "annual_attrition_rate",
                "label": "Annual Attrition Rate",
                "value": DEFAULT_ASSUMPTIONS.annual_attrition_rate,
                "unit": "%",
                "display_value": f"{DEFAULT_ASSUMPTIONS.annual_attrition_rate * 100:.0f}%",
                "description": "Percentage of employees expected to depart annually, applied evenly across months.",
                "used_in": "forecast_engine.py — monthly attrition = annual rate / 12, applied to each cost center.",
            },
        ],
    },
    {
        "name": "Benefits",
        "category": "benefits",
        "items": [
            {
                "name": "benefits_load_pct",
                "label": "Benefits Load",
                "value": DEFAULT_ASSUMPTIONS.benefits_load_pct,
                "unit": "%",
                "display_value": f"{DEFAULT_ASSUMPTIONS.benefits_load_pct * 100:.0f}%",
                "description": "Employer-paid benefits as a percentage of base salary (health, dental, vision, 401k match).",
                "used_in": "forecast_engine.py — benefits = base_salary × benefits_load / 12 per month.",
            },
        ],
    },
    {
        "name": "Payroll Tax",
        "category": "payroll_tax",
        "items": [
            {
                "name": "fica_rate",
                "label": "FICA Rate",
                "value": DEFAULT_ASSUMPTIONS.fica_rate,
                "unit": "%",
                "display_value": f"{DEFAULT_ASSUMPTIONS.fica_rate * 100:.2f}%",
                "description": "Combined employer Social Security (6.2%) and Medicare (1.45%) rate.",
                "used_in": "forecast_engine.py — applied to earnings up to the FICA wage base.",
            },
            {
                "name": "fica_wage_base",
                "label": "FICA Wage Base",
                "value": DEFAULT_ASSUMPTIONS.fica_wage_base,
                "unit": "$",
                "display_value": f"${DEFAULT_ASSUMPTIONS.fica_wage_base:,.0f}",
                "description": "Annual earnings cap for Social Security tax. Medicare applies above this with no cap.",
                "used_in": "forecast_engine.py — SS portion stops at this threshold; Medicare-only rate above it.",
            },
            {
                "name": "medicare_only_rate",
                "label": "Medicare-Only Rate",
                "value": DEFAULT_ASSUMPTIONS.medicare_only_rate,
                "unit": "%",
                "display_value": f"{DEFAULT_ASSUMPTIONS.medicare_only_rate * 100:.2f}%",
                "description": "Medicare tax rate applied to earnings above the FICA wage base.",
                "used_in": "forecast_engine.py — replaces FICA rate for the portion above wage base.",
            },
        ],
    },
    {
        "name": "Bonus",
        "category": "bonus",
        "items": [
            {
                "name": "bonus_targets",
                "label": "Bonus Target by Level",
                "value": {"L3": 8, "L4": 10, "L5": 15, "L6": 20, "L7": 25},
                "unit": "% of salary",
                "display_value": "L3: 8%, L4: 10%, L5: 15%, L6: 20%, L7: 25%",
                "description": "Target bonus as a percentage of base salary, accrued monthly.",
                "used_in": "forecast_engine.py — bonus = salary × target_pct / 100 / 12 per month.",
            },
        ],
    },
    {
        "name": "Hire Pace",
        "category": "hire_pace",
        "items": [
            {
                "name": "quarterly_hire_growth",
                "label": "Quarterly Hire Growth",
                "value": DEFAULT_ASSUMPTIONS.quarterly_hire_growth,
                "unit": "%",
                "display_value": f"{DEFAULT_ASSUMPTIONS.quarterly_hire_growth * 100:.0f}%",
                "description": "Percentage of total headcount added as new hires each quarter, spread across 3 months.",
                "used_in": "forecast_engine.py — new hires = headcount × rate / 3, distributed across cost centers.",
            },
        ],
    },
]
