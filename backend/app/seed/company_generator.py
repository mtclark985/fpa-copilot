"""Generate a realistic 500-person demo company.

Produces 20 cost centers in a 3-level hierarchy and 500 employees
with realistic comp bands, hire dates, and location distributions.
Deterministic via fixed random seed for reproducible demos.
"""

import datetime
import random

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_center import CostCenter
from app.models.employee import Employee
from app.models.position import Position

fake = Faker()
Faker.seed(42)
random.seed(42)

# 3-level org hierarchy: Division > Department > Team
ORG_HIERARCHY: list[dict[str, str | list[dict[str, str | list[str]]]]] = [
    {
        "name": "Technology",
        "code": "TECH",
        "departments": [
            {"name": "Platform Engineering", "code": "TECH-PLAT", "teams": ["Infrastructure", "DevOps"]},
            {"name": "Product Engineering", "code": "TECH-PROD", "teams": ["Frontend", "Backend", "Mobile"]},
            {"name": "Data Engineering", "code": "TECH-DATA", "teams": ["Analytics", "ML Platform"]},
        ],
    },
    {
        "name": "Product",
        "code": "PROD",
        "departments": [
            {"name": "Product Management", "code": "PROD-PM", "teams": ["Core Product"]},
            {"name": "Design", "code": "PROD-DES", "teams": ["UX Design"]},
        ],
    },
    {
        "name": "Go-to-Market",
        "code": "GTM",
        "departments": [
            {"name": "Sales", "code": "GTM-SLS", "teams": ["Enterprise Sales", "Mid-Market"]},
            {"name": "Marketing", "code": "GTM-MKT", "teams": ["Growth Marketing"]},
            {"name": "Customer Success", "code": "GTM-CS", "teams": ["CS Operations"]},
        ],
    },
    {
        "name": "Corporate",
        "code": "CORP",
        "departments": [
            {"name": "Finance", "code": "CORP-FIN", "teams": ["FP&A"]},
            {"name": "HR", "code": "CORP-HR", "teams": ["People Ops"]},
            {"name": "Legal", "code": "CORP-LEG", "teams": ["Compliance"]},
        ],
    },
]

# Comp bands by job level (base salary ranges)
COMP_BANDS: dict[str, tuple[int, int]] = {
    "L3": (70_000, 100_000),
    "L4": (95_000, 135_000),
    "L5": (125_000, 180_000),
    "L6": (165_000, 240_000),
    "L7": (220_000, 320_000),
}

# Bonus targets by level
BONUS_TARGETS: dict[str, float] = {
    "L3": 8.0,
    "L4": 10.0,
    "L5": 15.0,
    "L6": 20.0,
    "L7": 25.0,
}

# Location distribution and cost-of-living multipliers
LOCATIONS: list[tuple[str, float, float]] = [
    ("Charlotte", 0.40, 0.90),  # 40% of employees, 0.90x COL
    ("NYC", 0.30, 1.20),        # 30%, 1.20x COL
    ("Remote", 0.30, 1.00),     # 30%, 1.00x COL
]

# Target headcount distribution by cost center code prefix
HEADCOUNT_WEIGHTS: dict[str, int] = {
    "TECH": 55,  # Technology is largest
    "PROD": 12,
    "GTM": 23,
    "CORP": 10,
}

# Level distribution (approximates a typical pyramid)
LEVEL_WEIGHTS: dict[str, int] = {
    "L3": 35,
    "L4": 30,
    "L5": 20,
    "L6": 10,
    "L7": 5,
}


def _pick_location() -> tuple[str, float]:
    """Pick a location weighted by distribution, return (name, col_multiplier)."""
    roll = random.random()
    cumulative = 0.0
    for name, weight, multiplier in LOCATIONS:
        cumulative += weight
        if roll < cumulative:
            return name, multiplier
    return LOCATIONS[-1][0], LOCATIONS[-1][2]


def _pick_level() -> str:
    """Pick a job level weighted by typical org pyramid."""
    levels = list(LEVEL_WEIGHTS.keys())
    weights = list(LEVEL_WEIGHTS.values())
    return random.choices(levels, weights=weights, k=1)[0]


def _generate_salary(level: str, col_multiplier: float) -> float:
    """Generate a salary within band, adjusted for cost of living."""
    low, high = COMP_BANDS[level]
    base = random.randint(low, high)
    return round(base * col_multiplier / 1000) * 1000  # round to nearest $1k


def _generate_hire_date() -> datetime.date:
    """Generate a hire date over the last 10 years with realistic distribution.

    Weights toward more recent hires — typical of a growing company.
    """
    days_ago = int(random.triangular(30, 3650, 365))
    return datetime.date(2026, 1, 1) - datetime.timedelta(days=days_ago)


async def generate_company(session: AsyncSession) -> dict[str, int]:
    """Seed the database with a complete demo company.

    Returns counts of created entities for verification.
    """
    # Step 1: Create cost centers
    cost_centers: list[CostCenter] = []
    team_cost_centers: list[CostCenter] = []

    for division in ORG_HIERARCHY:
        div_cc = CostCenter(
            code=str(division["code"]),
            name=str(division["name"]),
            vp_owner=fake.name(),
        )
        session.add(div_cc)
        await session.flush()
        cost_centers.append(div_cc)

        departments = division["departments"]
        assert isinstance(departments, list)
        for dept in departments:
            assert isinstance(dept, dict)
            dept_cc = CostCenter(
                code=str(dept["code"]),
                name=str(dept["name"]),
                parent_id=div_cc.id,
                vp_owner=fake.name(),
            )
            session.add(dept_cc)
            await session.flush()
            cost_centers.append(dept_cc)

            teams = dept["teams"]
            assert isinstance(teams, list)
            for team_name in teams:
                assert isinstance(team_name, str)
                team_code = f"{dept['code']}-{team_name[:4].upper()}"
                team_cc = CostCenter(
                    code=team_code,
                    name=str(team_name),
                    parent_id=dept_cc.id,
                    vp_owner=dept_cc.vp_owner,
                )
                session.add(team_cc)
                await session.flush()
                cost_centers.append(team_cc)
                team_cost_centers.append(team_cc)

    # Step 2: Distribute 500 employees across team-level cost centers
    # Weight by division
    team_weights: list[float] = []
    for tcc in team_cost_centers:
        prefix = tcc.code.split("-")[0]
        team_weights.append(float(HEADCOUNT_WEIGHTS.get(prefix, 10)))

    total_weight = sum(team_weights)
    team_targets = [max(3, int(500 * w / total_weight)) for w in team_weights]

    # Adjust to hit exactly 500
    diff = 500 - sum(team_targets)
    for i in range(abs(diff)):
        idx = i % len(team_targets)
        team_targets[idx] += 1 if diff > 0 else -1

    employees_created = 0
    emp_number = 1

    for tcc, target_count in zip(team_cost_centers, team_targets):
        for _ in range(target_count):
            level = _pick_level()
            location, col_mult = _pick_location()
            salary = _generate_salary(level, col_mult)

            emp = Employee(
                employee_number=f"E{emp_number:04d}",
                name=fake.name(),
                hire_date=_generate_hire_date(),
                cost_center_id=tcc.id,
                job_level=level,
                base_salary=salary,
                bonus_target_pct=BONUS_TARGETS[level],
                location=location,
            )
            session.add(emp)
            emp_number += 1
            employees_created += 1

    await session.flush()

    # Step 3: Create ~25 open positions (5% of headcount)
    positions_created = 0
    for tcc in team_cost_centers:
        if random.random() < 0.6:  # ~60% of teams have open positions
            num_open = random.randint(1, 3)
            for _ in range(num_open):
                level = _pick_level()
                # Target start dates spread over next 6 months
                days_future = random.randint(15, 180)
                target_date = datetime.date(2026, 1, 1) + datetime.timedelta(days=days_future)

                pos = Position(
                    cost_center_id=tcc.id,
                    job_level=level,
                    status="open",
                    target_start_date=target_date,
                )
                session.add(pos)
                positions_created += 1

    await session.flush()
    await session.commit()

    return {
        "cost_centers": len(cost_centers),
        "employees": employees_created,
        "open_positions": positions_created,
    }
