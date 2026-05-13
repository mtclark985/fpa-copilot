# Run Log — Run 1

## Phase 1: Project Scaffolding
**Completed:** 2026-05-13

- Initialized git repo, .gitignore, .env.example, README.md
- Docker Compose with Postgres 16 — verified `docker compose up` works and DB is connectable
- Backend: FastAPI app with `/api/v1/health`, SQLAlchemy async engine, Alembic config, pydantic-settings config
- Frontend: Vite + React 18 + TypeScript + Tailwind CSS v4 + TanStack Query + React Router
- Dashboard page fetches /api/v1/health and displays status
- Test: health endpoint test passes
- Note: System has Python 3.14.4 — added setuptools build-backend to pyproject.toml for compatibility
- **Commit:** `feat(phase-1): project scaffolding`

## Phase 2: Data Model and Migrations
**Completed:** 2026-05-13

- Defined 7 ORM models: CostCenter, Employee, Position, ForecastVersion, ForecastLine, Actual, Variance
- All models have type hints, relationships, FK indexes
- Alembic auto-generated migration applied cleanly
- 7 tests pass (6 model CRUD tests + 1 health endpoint)
- Used `datetime.datetime.utcnow` for default timestamps (naive) to avoid asyncpg timezone mismatch
- **Commit:** `feat(phase-2): data model and migrations`

## Phase 3: Demo Company Generator
**Completed:** 2026-05-13

- Built `seed/company_generator.py` with 3-level org hierarchy (4 divisions → 11 depts → 16 teams = 31 CCs)
- 500 employees with realistic comp bands, L3-L7 levels, 3 locations (Charlotte/NYC/Remote) with COL adjustments
- ~28 open positions across teams
- Deterministic via `random.seed(42)` + `Faker.seed(42)`
- CLI `scripts/seed_company.py` wipes and reseeds
- 5 smoke tests all pass
- **Commit:** `feat(phase-3): demo company generator`

