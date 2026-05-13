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

## Phase 4: Forecast Engine
**Completed:** 2026-05-13

- Built driver-based forecast: salary roll-forward, merit (April 4%), hires, attrition (12%/yr), bonus, benefits (18%), FICA/Medicare
- Year 1 breakdown: $73M salary + $10M bonus + $13M benefits + $5M taxes = $101M all-in
- GET /api/v1/forecast endpoint with period/cost_center filters
- 3 math tests pass (FICA below/above wage base, single-employee forecast)
- **Commit:** `feat(phase-4): driver-based forecast engine`

## Phase 5: Monthly Simulator and Actuals Ingestion
**Completed:** 2026-05-13

- Monthly simulator with story variances (one per month), random hires/departures, payroll noise
- 6 months pre-seeded: Jan-Jun 2026 with ~2000 actual records each
- Actuals API, advance-month endpoint
- 3 simulator tests pass
- **Commit:** `feat(phase-5): monthly simulator and actuals ingestion`

## Phase 6: Variance Calculation
**Completed:** 2026-05-13

- Variance calculator with volume/rate decomposition and materiality scoring (0-100)
- Calculated 76-100 variances per month across 6 seeded months
- API: GET /variances (with filters), GET /variances/{id}, POST /variances/{period}/calculate
- 3 tests: existence, decomposition integrity, score range
- **Commit:** `feat(phase-6): variance calculation with volume/rate decomposition`

## Phase 7: Variance Detection Agent
**Completed:** 2026-05-13

- Agent base class with Anthropic API wrapping, Pydantic output parsing, logging
- VarianceDetectorAgent: reviews material variances with prior-month context
- Output: severity, unexpectedness, rationale, suggested_action per variance
- Advance-month endpoint now chains: simulate -> variance calc -> agent analysis
- ANTHROPIC_API_KEY not set — agent tests use mocked responses (5 tests pass)
- Agent will run live against seeded data once API key is provided
- All 29 tests passing
- **Commit:** `feat(phase-7): variance detection agent`

## Phase 8: Frontend UI Shell
**Completed:** 2026-05-13

- Dashboard: KPI cards (month, headcount, YTD actuals/variance, FY landing), actual-vs-forecast chart, agent activity feed
- Forecast: cost center x month table with CC/category filters, CSV export
- Variances: list sorted by materiality, drill-down panel with volume/rate decomposition and agent assessment
- Close: advance-month button triggers simulate -> variance calc -> agent chain
- Navigation shell with TanStack Query, clean routing
- Backend: added /kpis/dashboard, /employees, /cost-centers endpoints
- All 29 tests pass, TypeScript compiles clean
- **Commit:** `feat(phase-8): frontend UI shell`

## Phase 9: Polish and Documentation
**Completed:** 2026-05-13

- README.md: project description, tech stack, quick start, demo script, architecture overview, roadmap
- docs/architecture.md: system diagram, layer descriptions, data flow, API contracts
- DECISIONS.md: 8 non-trivial decisions documented with rationale
- scripts/setup_demo.py: one-shot setup (seed + forecast + 6 months + variances)
- Verified: clean setup_demo.py run produces working data, all 29 tests pass, frontend compiles clean
- **Commit:** `docs(phase-9): readme and polish`

## Run 1 Summary

All 9 phases completed. Final state:
- 29 backend tests passing
- Frontend TypeScript compiles clean (0 errors)
- `docker compose up` + `python scripts/setup_demo.py` + `npm run dev` = working app
- Dashboard, Forecast, Variances, Close pages render with real data
- Variance Detection Agent built and tested (mocked) — runs live when ANTHROPIC_API_KEY set
- No [WIP] commits

---

# Run Log — Run 2

## Phase 1: Branch Setup and Working Agreements
**Started:** 2026-05-13

- Created branch `run-2-approval-workflow` from main
- Read all Section 0 files: RUN_LOG.md, DECISIONS.md, base.py, variance_detector.py, variance_calculator.py, variances.py, Variances.tsx, api.ts
- Confirmed understanding of Run 1 architecture and Run 2 goals
- Verified app runs end-to-end (docker, backend, frontend)

