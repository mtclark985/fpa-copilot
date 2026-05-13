\# FP\&A Copilot — Run 1 Spec



\*\*Author:\*\* Michael Clark

\*\*Run:\*\* 1 of \~4

\*\*Estimated autonomous runtime:\*\* 6-8 hours

\*\*Goal of this run:\*\* Build the foundation — data model, seeded demo company, actuals ingestion, one working variance detection agent, and a UI shell that proves the architecture works end-to-end.



\---



\## 1. Project Context



\*\*Project name:\*\* FP\&A Copilot



\*\*One-line description:\*\* A living forecast platform where the comp expense forecast continuously updates itself as actuals arrive, with AI agents proposing changes that humans approve.



\*\*Why this exists:\*\* Enterprise FP\&A tools claim to offer rolling forecasts and AI-driven analysis, but in practice forecasts and actuals live in separate worlds with manual monthly "actualization" cycles. The result is FP\&A teams spending the first two weeks of every month doing reconciliation work that should be automated, and the last two weeks writing variance commentary that an LLM could draft in seconds. This tool demonstrates what FP\&A \*should\* look like in 2026.



\*\*Who the user is:\*\* A Finance Director or FP\&A Manager at a 500-5000 person company, responsible for headcount and comp expense forecasting. They run a monthly close cycle and produce variance commentary for executive review.



\*\*Portfolio framing for interviews:\*\* "I built the AI-native version of the FP\&A tool I use every day, designed around the principle that the forecast should be a living artifact, not a quarterly artifact."



\---



\## 2. Tech Stack



\*\*Backend:\*\*

\- Python 3.11+

\- FastAPI (latest)

\- SQLAlchemy 2.0 (async)

\- Alembic for migrations

\- Pydantic v2 for schemas

\- `anthropic` SDK (latest) for agent calls

\- `pandas` for data manipulation

\- `pytest` + `pytest-asyncio` for tests



\*\*Frontend:\*\*

\- React 18 + Vite

\- TypeScript

\- TanStack Query for data fetching

\- Tailwind CSS for styling

\- shadcn/ui for components

\- Recharts for visualizations



\*\*Database:\*\*

\- PostgreSQL 16 (via Docker for local dev)

\- Connection via SQLAlchemy async + asyncpg



\*\*Auth (this run):\*\*

\- None. Single-user demo. Add basic auth in Run 4.



\*\*Deployment target:\*\*

\- Local Docker Compose for now. Vercel + Railway/Render in Run 4.



\*\*Why these choices:\*\* Python/FastAPI is the dominant backend for AI-heavy applications and signals the right skillset for AI-in-Finance roles. React + Tailwind + shadcn produces a polished UI fast without custom design work. Postgres reflects real enterprise FP\&A infrastructure. Async throughout because agent calls are I/O bound.



\---



\## 3. Architecture \& File Structure



\*\*High-level architecture:\*\* Monorepo with `backend/` (FastAPI service) and `frontend/` (React app). Postgres in Docker. Agents are plain Python classes that wrap Anthropic API calls — no framework. Each agent has a single responsibility and returns structured Pydantic models. An Orchestrator class composes agents into workflows.



```

fpa-copilot/

├── README.md

├── SPEC.md                          # this file

├── RUN\_LOG.md                       # appended during the run

├── DECISIONS.md                     # non-trivial decisions

├── docker-compose.yml               # postgres for local dev

├── .env.example

├── backend/

│   ├── pyproject.toml

│   ├── alembic.ini

│   ├── alembic/

│   │   └── versions/

│   ├── app/

│   │   ├── \_\_init\_\_.py

│   │   ├── main.py                  # FastAPI app factory

│   │   ├── config.py                # settings via pydantic-settings

│   │   ├── db.py                    # async engine + session

│   │   ├── models/                  # SQLAlchemy ORM models

│   │   │   ├── employee.py

│   │   │   ├── cost\_center.py

│   │   │   ├── forecast.py

│   │   │   ├── actual.py

│   │   │   └── variance.py

│   │   ├── schemas/                 # Pydantic API schemas

│   │   ├── api/                     # FastAPI routers

│   │   │   ├── employees.py

│   │   │   ├── forecast.py

│   │   │   ├── actuals.py

│   │   │   ├── variances.py

│   │   │   └── close.py

│   │   ├── services/                # business logic

│   │   │   ├── forecast\_engine.py

│   │   │   ├── actuals\_ingestion.py

│   │   │   └── variance\_calculator.py

│   │   ├── agents/                  # AI agents

│   │   │   ├── base.py              # shared agent infrastructure

│   │   │   └── variance\_detector.py # the agent built in this run

│   │   ├── seed/                    # demo data generation

│   │   │   ├── company\_generator.py

│   │   │   └── monthly\_simulator.py

│   │   └── tests/

│   └── scripts/

│       ├── seed\_company.py          # CLI: generate the fictional company

│       └── simulate\_month.py        # CLI: advance to next month

├── frontend/

│   ├── package.json

│   ├── vite.config.ts

│   ├── tsconfig.json

│   ├── tailwind.config.js

│   ├── index.html

│   └── src/

│       ├── main.tsx

│       ├── App.tsx

│       ├── lib/

│       │   ├── api.ts               # API client

│       │   └── utils.ts

│       ├── components/

│       │   └── ui/                  # shadcn components

│       ├── pages/

│       │   ├── Dashboard.tsx

│       │   ├── Forecast.tsx

│       │   ├── Variances.tsx

│       │   └── Close.tsx

│       └── types/

│           └── api.ts               # generated from backend

```



\*\*Naming conventions:\*\*

\- Python: `snake\_case` files, `PascalCase` classes, `snake\_case` functions

\- TypeScript: `PascalCase` for components and types, `camelCase` for everything else

\- API routes: `/api/v1/<resource>` plural, RESTful

\- Database tables: `snake\_case` plural (`employees`, `cost\_centers`)



\*\*Code style:\*\*

\- Backend: `ruff` for lint+format, `mypy --strict` for type checking

\- Frontend: `eslint` + `prettier`, strict TS

\- Every public function has a docstring with rationale, not just description

\- No `Any` in either codebase



\---



\## 4. Scope: What's In and What's Out for Run 1



\*\*In scope for Run 1:\*\*

\- Demo company generator: 500 employees, 20 cost centers, realistic comp bands, org hierarchy

\- Forecast engine: driver-based comp expense forecast for the next 18 months, generated from baseline org + hiring plan + attrition assumptions + merit cycle

\- Actuals ingestion: ability to advance the simulated clock one month and ingest synthesized payroll actuals

\- Variance calculation: line-item variance between forecast and actuals at cost-center × month granularity, with decomposition into volume vs. rate variance

\- One agent: Variance Detection Agent — flags material and unexpected variances with reasoning

\- UI: Dashboard (KPIs), Forecast view (table + chart), Variances view (list + drill-down with agent reasoning)

\- Seeded with the company at "January 2026" and 6 months of actuals already loaded so the app has something to show on first launch

\- End-to-end working: `docker compose up` + `npm run dev` and the app loads with data



\*\*Out of scope for Run 1 (deferred to later runs):\*\*

\- Variance Attribution Agent (Run 2) — explains \*why\* variances happened

\- Forecast Update Proposal Agent (Run 2) — proposes forward forecast changes

\- Approval workflow UI (Run 2)

\- Close report generation (Run 3)

\- Commentary writing agent (Run 3)

\- Auth, multi-user, deployment (Run 4)

\- Revenue, opex, capex (post-portfolio expansion)



\*\*Stub or mock instead of build:\*\*

\- No external data sources — all data synthesized internally

\- No real payroll system integration — payroll actuals generated by the monthly simulator

\- No Snowflake or warehouse — Postgres is the warehouse for now



\---



\## 5. Phased Build Plan



\### Phase 1: Project scaffolding

\*\*Goal:\*\* Repo structure, dependency management, Docker Compose with Postgres, FastAPI hello-world, React hello-world, both talking to each other.



\*\*Tasks:\*\*

1\. Initialize git repo, create README, .gitignore, .env.example

2\. Set up `docker-compose.yml` with Postgres 16

3\. Initialize backend with `pyproject.toml`, install dependencies, FastAPI hello world at `/api/v1/health`

4\. Set up Alembic, create initial empty migration

5\. Initialize frontend with Vite + React + TS + Tailwind + shadcn

6\. Add a single `Dashboard` page that fetches `/api/v1/health` and displays status

7\. Verify end-to-end: `docker compose up`, backend on :8000, frontend on :5173, dashboard shows "API healthy"



\*\*Definition of done:\*\*

\- \[ ] `docker compose up` starts Postgres successfully

\- \[ ] `uvicorn app.main:app --reload` starts backend

\- \[ ] `npm run dev` starts frontend

\- \[ ] Frontend dashboard loads and shows API health

\- \[ ] First commit: `feat(phase-1): project scaffolding`



\### Phase 2: Data model and migrations

\*\*Goal:\*\* Define all SQLAlchemy models and generate Alembic migrations. No business logic yet.



\*\*Tasks:\*\*

1\. Define `CostCenter` model (id, code, name, parent\_id, vp\_owner)

2\. Define `Employee` model (id, employee\_number, name, hire\_date, termination\_date, cost\_center\_id, job\_level, base\_salary, bonus\_target\_pct, location)

3\. Define `Position` model (id, cost\_center\_id, job\_level, status \[open/filled], target\_start\_date)

4\. Define `ForecastVersion` model (id, name, created\_at, is\_active)

5\. Define `ForecastLine` model (id, version\_id, cost\_center\_id, period \[YYYY-MM], category \[salary/bonus/benefits/taxes/other], amount, headcount\_eop)

6\. Define `Actual` model (id, employee\_id, period, category, amount)

7\. Define `Variance` model (id, forecast\_version\_id, cost\_center\_id, period, category, forecast\_amount, actual\_amount, variance\_amount, variance\_pct, volume\_variance, rate\_variance, materiality\_score, detected\_at)

8\. Generate Alembic migration, apply it

9\. Write unit tests confirming models can be created and queried



\*\*Definition of done:\*\*

\- \[ ] `alembic upgrade head` runs clean

\- \[ ] All models have type hints, relationships, and indexes on FKs

\- \[ ] Tests pass: `pytest backend/app/tests/test\_models.py`

\- \[ ] Commit: `feat(phase-2): data model and migrations`



\### Phase 3: Demo company generator

\*\*Goal:\*\* Generate a believable 500-person company seeded into Postgres.



\*\*Tasks:\*\*

1\. Build `seed/company\_generator.py` that produces:

&#x20;  - 20 cost centers in a realistic 3-level hierarchy (e.g., Technology > Engineering > Platform Engineering)

&#x20;  - 500 employees distributed across cost centers with realistic ratios (Engineering largest, Finance and HR smaller)

&#x20;  - Realistic comp bands by job level (L3 through L7+) and location (use 3 locations: Charlotte, NYC, Remote with cost-of-living differentials)

&#x20;  - Hire dates spread over the last 10 years with realistic distribution

&#x20;  - 5% of positions marked as open with target\_start\_dates in the next 6 months

2\. Names: use `faker` library

3\. Build `scripts/seed\_company.py` CLI that wipes and reseeds

4\. Make seed deterministic (fixed random seed) so the demo is reproducible

5\. Write a smoke test that confirms post-seed counts and a few invariants (every employee has a cost center, comp is within band, etc.)



\*\*Definition of done:\*\*

\- \[ ] `python scripts/seed\_company.py` produces 500 employees, 20 cost centers, \~25 open positions

\- \[ ] Data passes invariant checks

\- \[ ] Commit: `feat(phase-3): demo company generator`



\### Phase 4: Forecast engine

\*\*Goal:\*\* Generate an 18-month driver-based comp expense forecast from the seeded company.



\*\*Tasks:\*\*

1\. Build `services/forecast\_engine.py` with:

&#x20;  - Baseline: roll forward current employees with projected merit cycle in April (4% avg, with normal distribution)

&#x20;  - Hires: project open positions onto their target\_start\_date; add planned hires beyond that as a flat assumption (2% of headcount per quarter)

&#x20;  - Attrition: apply 12% annual attrition rate, distributed monthly, weighted toward newer employees

&#x20;  - Bonus: target bonus % accrued monthly, paid out in February (FY bonus assumption)

&#x20;  - Benefits: 18% load on base salary

&#x20;  - Taxes: 7.65% FICA on first $168k, plus 1.45% Medicare

2\. Output: ForecastLine rows at cost\_center × month × category granularity

3\. Save as ForecastVersion named "Initial Plan FY26"

4\. Build `GET /api/v1/forecast` endpoint to retrieve forecast

5\. Write tests on the math: a single employee, projected forward, should produce predictable numbers



\*\*Definition of done:\*\*

\- \[ ] Forecast generates without errors

\- \[ ] Spot-check: total Year 1 comp expense is within reasonable bounds for a 500-person company (\~$60-80M)

\- \[ ] API endpoint returns forecast data

\- \[ ] Math tests pass

\- \[ ] Commit: `feat(phase-4): driver-based forecast engine`



\### Phase 5: Actuals ingestion and monthly simulator

\*\*Goal:\*\* Simulate the passage of time. Each "month" advance generates payroll actuals that intentionally diverge from forecast in interesting ways.



\*\*Tasks:\*\*

1\. Build `seed/monthly\_simulator.py` that for a given month:

&#x20;  - Generates payroll actuals for every active employee (base salary / 12, plus benefits, taxes)

&#x20;  - Introduces realistic deviations:

&#x20;    - 1-2 unplanned hires per month (will create positive variance)

&#x20;    - 1-2 unplanned departures (negative variance)

&#x20;    - Occasional retention bonuses or off-cycle adjustments (rate variance)

&#x20;    - One "story" variance per month: a specific narrative event (e.g., "May: Risk team backfilled 4 open positions early")

&#x20;  - Updates employee status (terminations, new hires)

2\. Build `services/actuals\_ingestion.py` that processes the simulator output and writes Actual rows

3\. Build `scripts/simulate\_month.py` CLI that advances one month

4\. Pre-seed with 6 months of history (Jan-June 2026) so the app has variance data on first load

5\. Build `POST /api/v1/close/advance-month` endpoint to trigger from UI later

6\. Tests: simulator is deterministic given a seed; actuals respect business rules



\*\*Definition of done:\*\*

\- \[ ] `python scripts/simulate\_month.py` advances one month, generates actuals

\- \[ ] Running 6 times produces 6 months of actuals with deliberate variances

\- \[ ] Each month's actuals are queryable via API

\- \[ ] Commit: `feat(phase-5): monthly simulator and actuals ingestion`



\### Phase 6: Variance calculation

\*\*Goal:\*\* Calculate forecast-vs-actual variance with volume/rate decomposition.



\*\*Tasks:\*\*

1\. Build `services/variance\_calculator.py`:

&#x20;  - For each closed period × cost\_center × category, calculate variance = actual - forecast

&#x20;  - Decompose into volume variance (headcount delta × forecast rate) and rate variance (actual headcount × rate delta)

&#x20;  - Calculate materiality\_score: combination of absolute dollar size, % variance, and unexpectedness (how far from historical pattern)

2\. Trigger variance calculation automatically after `simulate\_month`

3\. Build `GET /api/v1/variances` endpoint with filters (period, cost\_center, min\_materiality)

4\. Tests: known-input variance produces known-output decomposition



\*\*Definition of done:\*\*

\- \[ ] Variances calculated and stored for all 6 historical months

\- \[ ] API returns variances with proper filtering

\- \[ ] Math is correct (verified with a hand-calculated test case)

\- \[ ] Commit: `feat(phase-6): variance calculation with volume/rate decomposition`



\### Phase 7: Variance Detection Agent

\*\*Goal:\*\* First AI agent. Reviews variances and produces a structured assessment of which deserve human attention and why.



\*\*Tasks:\*\*

1\. Build `agents/base.py` with a shared `Agent` base class:

&#x20;  - Wraps Anthropic API call

&#x20;  - Standardized prompt structure (system prompt, context, task, output format)

&#x20;  - Returns Pydantic model

&#x20;  - Logs every call for traceability

2\. Build `agents/variance\_detector.py`:

&#x20;  - Input: list of calculated variances for a period, plus 3 months of prior context

&#x20;  - System prompt: experienced FP\&A analyst reviewing month-end variance

&#x20;  - Output structure: `VarianceAssessment` with fields per variance: severity (low/medium/high), unexpectedness (expected/somewhat unexpected/highly unexpected), one-sentence rationale, suggested\_action (monitor / investigate / escalate)

&#x20;  - Use Claude Sonnet 4 model

3\. Build `POST /api/v1/variances/{period}/analyze` endpoint that triggers the agent and stores results

4\. Run the agent against the 6 pre-seeded months as part of initial data load

5\. Tests: agent returns valid Pydantic output for a known input fixture (use VCR-style cassette for the API call to avoid burning tokens in CI)



\*\*Definition of done:\*\*

\- \[ ] Agent runs successfully against real variance data

\- \[ ] Output is valid Pydantic, persisted to DB

\- \[ ] Reasoning quality is reasonable on spot-check (the "story" variance from each month should be flagged as high severity / highly unexpected)

\- \[ ] API endpoint works

\- \[ ] Commit: `feat(phase-7): variance detection agent`



\### Phase 8: Frontend — Dashboard, Forecast view, Variance view

\*\*Goal:\*\* Polished UI shell that lets a user navigate the system.



\*\*Tasks:\*\*

1\. \*\*Dashboard page:\*\*

&#x20;  - Top KPI cards: Current Month, Headcount EOP, YTD Comp Actuals, YTD Variance to Plan, Forecasted FY Landing

&#x20;  - Chart: monthly actual vs. forecast comp expense (Recharts line + bar combo)

&#x20;  - "Recent agent activity" list showing the latest variance assessments

2\. \*\*Forecast page:\*\*

&#x20;  - Table: cost center × month, with category drill-down

&#x20;  - Filter by cost center, by category

&#x20;  - Export to CSV button

3\. \*\*Variances page:\*\*

&#x20;  - List view: all variances for the most recent closed month, sorted by materiality

&#x20;  - Each row shows: cost center, category, variance $, variance %, severity badge, agent rationale

&#x20;  - Drill-down panel on row click: full variance decomposition (volume vs. rate), historical trend, full agent reasoning

4\. \*\*Close page (placeholder for Run 2):\*\*

&#x20;  - Single button: "Advance to next month" → triggers `simulate\_month` → triggers `analyze` → refreshes dashboard

5\. Wire up TanStack Query for all data fetching

6\. Make it look good: clean typography, consistent spacing, proper loading states, error boundaries



\*\*Definition of done:\*\*

\- \[ ] All 4 pages render and route correctly

\- \[ ] Dashboard shows real KPIs from the database

\- \[ ] Forecast and Variance tables are populated with real data

\- \[ ] Advance month button works end-to-end

\- \[ ] No console errors

\- \[ ] UI looks polished, not like a generic admin template

\- \[ ] Commit: `feat(phase-8): frontend UI shell`



\### Phase 9: Polish and documentation

\*\*Goal:\*\* Tighten loose ends, write the README, make first impression strong.



\*\*Tasks:\*\*

1\. README.md with: project description, screenshots (placeholders for now, you'll add real ones), architecture diagram (ASCII or describe), tech stack, setup instructions, demo script ("here's what to click to see the magic")

2\. Verify clean install works: fresh clone, `docker compose up`, `python scripts/seed\_company.py \&\& python scripts/simulate\_month.py` × 6, frontend works

3\. Make sure RUN\_LOG.md and DECISIONS.md are populated and useful

4\. One-page architecture doc in `docs/architecture.md`

5\. Commit: `docs(phase-9): readme and polish`



\*\*Definition of done:\*\*

\- \[ ] Fresh clone + setup works in under 5 minutes

\- \[ ] README is interview-grade (someone reading it should immediately understand what this is and want to see more)

\- \[ ] All tests pass

\- \[ ] All previous DoD checkboxes still satisfied



\---



\## 6. Data Model (Reference)



```

CostCenter (id, code, name, parent\_id, vp\_owner)

&#x20; ├── has many → Employee

&#x20; ├── has many → Position

&#x20; ├── has many → ForecastLine

&#x20; └── has many → Variance



Employee (id, employee\_number, name, hire\_date, termination\_date, cost\_center\_id, job\_level, base\_salary, bonus\_target\_pct, location)

&#x20; └── has many → Actual



Position (id, cost\_center\_id, job\_level, status, target\_start\_date)



ForecastVersion (id, name, created\_at, is\_active)

&#x20; └── has many → ForecastLine



ForecastLine (id, version\_id, cost\_center\_id, period, category, amount, headcount\_eop)



Actual (id, employee\_id, period, category, amount)



Variance (id, forecast\_version\_id, cost\_center\_id, period, category, forecast\_amount, actual\_amount, variance\_amount, variance\_pct, volume\_variance, rate\_variance, materiality\_score, agent\_severity, agent\_unexpectedness, agent\_rationale, agent\_suggested\_action, detected\_at)

```



\*\*Key business rules:\*\*

\- An Employee with `termination\_date <= period\_end` does not contribute Actuals for that period

\- Variance materiality\_score is a 0-100 scale; threshold for "material" is 60

\- ForecastVersion `is\_active=True` is unique; only one active forecast at a time



\---



\## 7. API Contracts



| Method | Path | Purpose |

|--------|------|---------|

| GET | `/api/v1/health` | Health check |

| GET | `/api/v1/employees` | List employees, filterable by cost\_center |

| GET | `/api/v1/cost-centers` | List cost centers (with hierarchy) |

| GET | `/api/v1/forecast` | Get active forecast, filterable by period range, cost\_center |

| GET | `/api/v1/actuals` | Get actuals, filterable by period range |

| GET | `/api/v1/variances` | Get variances, filterable by period, cost\_center, min\_materiality |

| GET | `/api/v1/variances/{id}` | Get single variance with full agent reasoning |

| POST | `/api/v1/close/advance-month` | Run monthly simulator + variance calc + agent analysis |

| POST | `/api/v1/variances/{period}/analyze` | Re-run variance detection agent for a period |

| GET | `/api/v1/kpis/dashboard` | Aggregated KPIs for dashboard |



All responses are JSON. Errors return RFC 7807 problem detail format.



\---



\## 8. Testing Requirements



\- Unit tests for: forecast math, variance decomposition, agent output parsing

\- Integration tests for: API endpoints with test database

\- Use `pytest` + `pytest-asyncio` + `httpx.AsyncClient` for API tests

\- Use a fixture-based approach for agent tests (cassette the Anthropic response) so tests don't burn tokens

\- Run `pytest` after every phase; do not commit failing tests

\- Coverage target: 70%+ on `services/` and `agents/`



\---



\## 9. Working Agreements



\*\*Commit policy:\*\*

\- Commit after every completed phase, and after every meaningful sub-task within a phase

\- Conventional commits: `feat(scope):`, `fix(scope):`, `test(scope):`, `docs(scope):`, `refactor(scope):`

\- Never commit broken code without `\[WIP]` prefix and a note in RUN\_LOG.md



\*\*Logging policy:\*\*

\- `RUN\_LOG.md` at repo root, appended throughout the run

\- Each entry: timestamp, phase, what was done, files touched, notable decisions, any blockers

\- Aim for one entry per meaningful unit of work (every 15-30 min of execution)



\*\*When to stop and wait for human:\*\*

\- Any task requiring `ANTHROPIC\_API\_KEY` to be set when it isn't — stop and request it (Michael will provide via `.env`)

\- Any deletion of more than 10 files at once

\- Any change to the data model after Phase 2 is committed (data model is locked after Phase 2; structural changes need approval)

\- If the same test keeps failing after 3 attempts at fixing it — document the failure mode and move on, flagging it in RUN\_LOG.md

\- If `docker compose up` fails for environmental reasons (port conflicts, missing Docker) — document and stop



\*\*When NOT to stop:\*\*

\- Lint errors, type errors — fix them

\- Failing tests caused by code you just wrote — fix them

\- Missing Python or npm dependencies — install them

\- Minor UI design decisions (colors, spacing, layout within stated style) — make the call, document if non-obvious

\- Choices between two reasonable library options that both fit — pick the more popular one, document in DECISIONS.md



\*\*Decision log:\*\*

\- `DECISIONS.md` at repo root

\- Every time you make a non-trivial call (architecture, library, schema interpretation), add an entry with rationale

\- Future me reviewing the codebase should be able to understand why anything looks the way it does



\---



\## 10. Environment \& Secrets



\*\*`.env.example` should include:\*\*

```

DATABASE\_URL=postgresql+asyncpg://fpa:fpa@localhost:5432/fpa\_copilot

ANTHROPIC\_API\_KEY=sk-ant-...

APP\_ENV=development

LOG\_LEVEL=INFO

```



\*\*Required from Michael before agent phases run:\*\*

\- `ANTHROPIC\_API\_KEY` set in `.env`. If not set when Phase 7 begins, stop and document in `BLOCKERS.md`.



\*\*Never commit `.env` or hardcode API keys.\*\*



\---



\## 11. Definition of Done for Run 1



The run is successful when all of the following are true:

\- \[ ] All 9 phases complete

\- \[ ] `git log` shows clean conventional commits per phase

\- \[ ] `docker compose up` + `python scripts/seed\_company.py` + 6× `python scripts/simulate\_month.py` + `npm run dev` produces a fully working app

\- \[ ] Dashboard, Forecast, Variances, and Close pages all render with real data

\- \[ ] Variance Detection Agent has run against all 6 months of seeded data and stored assessments

\- \[ ] All tests pass

\- \[ ] README.md, RUN\_LOG.md, DECISIONS.md, and `docs/architecture.md` are complete and useful

\- \[ ] No `\[WIP]` commits remaining



If any DoD item is not met, document the gap in RUN\_LOG.md before ending the run.



\---



\## Starting Prompt for Claude Code



Paste this verbatim into Claude Code when kicking off the run:



```

Read SPEC.md in full before doing anything else. Confirm you understand the goal,

the phased build plan, and the working agreements in Section 9.



Then execute Phases 1 through 9 in order. For each phase:

1\. Read the phase tasks

2\. Implement them

3\. Run tests

4\. If everything in the phase's Definition of Done is satisfied, commit with the

&#x20;  format specified

5\. Append an entry to RUN\_LOG.md describing what was done

6\. Move to the next phase



Do not ask for approval on routine decisions. Follow the "when to stop" rules in

Section 9 strictly — stop only for the listed reasons, document the reason in

RUN\_LOG.md, and wait.



Start with Phase 1, Task 1. Go.

```



\---



\## Appendix: What Runs 2-4 Will Add



\*\*Run 2 — The Approval Workflow (the core differentiator):\*\*

\- Variance Attribution Agent (explains \*why\* each variance happened, tracing to drivers)

\- Forecast Update Proposal Agent (proposes specific forward-looking changes to the forecast)

\- Approval UI: each proposed change is a card with rationale, impact, accept/reject/modify buttons

\- New ForecastVersion created on accept; full audit trail of which proposals were accepted/rejected and why



\*\*Run 3 — The Monthly Close Experience:\*\*

\- Close Report Generation: 2-page executive memo per close, drafted by an agent, editable by user

\- Commentary Writing Agent

\- "One-click close" demo flow: press button → 90 seconds later → updated forecast + approval queue + draft memo

\- Polish: animations, loading states that feel intentional, demo mode



\*\*Run 4 — Production Polish:\*\*

\- Auth (Clerk or simple email+password)

\- Multi-tenant (multiple companies / multiple users per company)

\- Deployment to Vercel + Railway

\- Public demo URL with reset-every-hour seed data

\- README upgraded to portfolio piece with video walkthrough

