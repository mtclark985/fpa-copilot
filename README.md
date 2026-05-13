# FP&A Copilot

A living forecast platform where the comp expense forecast continuously updates itself as actuals arrive, with AI agents proposing changes that humans approve.

**The problem:** Enterprise FP&A teams spend the first two weeks of every month reconciling forecasts against actuals and the last two weeks writing variance commentary. This tool automates both.

**The approach:** Driver-based forecasting + synthetic payroll simulation + AI-powered variance detection = a working prototype of what FP&A should look like in 2026.

## What It Does

- **500-person demo company** seeded with realistic org structure, comp bands, and hiring plans
- **18-month driver-based forecast** incorporating merit cycles, attrition, new hires, bonus accruals, benefits, and payroll taxes
- **Monthly simulation** that generates payroll actuals with intentional variances (unplanned hires, departures, retention bonuses, off-cycle adjustments)
- **Variance calculation** with volume/rate decomposition and materiality scoring
- **AI variance detection** agent (Claude) that reviews each material variance and provides severity assessment, rationale, and suggested actions
- **AI variance attribution** agent that traces variances to specific drivers (early hires, departures, comp adjustments)
- **AI forecast proposal** agent that generates structured forecast update proposals from attributions
- **Approval workflow** — review, accept, reject, or modify-and-accept forecast change proposals
- **Forecast versioning** — each accepted proposal creates a new forecast version with full audit trail
- **Polished UI** with dashboard KPIs, forecast tables (with version selector), variance drill-down, proposals page, and one-click monthly close

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts |
| Database | PostgreSQL 16 (Docker) |
| AI | Anthropic Claude API (Sonnet) |
| Testing | pytest + pytest-asyncio |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- (Optional) Anthropic API key for AI agent features

### Setup

```bash
# 1. Start Postgres
docker compose up -d

# 2. Install backend dependencies
cd backend
pip install -e ".[dev]"

# 3. Seed the demo (creates company, forecast, 6 months of actuals + variances)
python scripts/setup_demo.py

# 4. Start the backend
python -m uvicorn app.main:app --reload --port 8000

# 5. In a new terminal — install and start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to see the app.

### Optional: Enable AI Agent

Create a `.env` file in the `backend/` directory:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Then use the Close page to advance months — the variance detection agent will analyze each month's variances.

## Demo Script

Here's what to click to see the system in action:

1. **Dashboard** — See KPI cards (headcount, YTD actuals), the actual-vs-forecast chart, active forecast version, and agent activity feed. If proposals are pending, a yellow banner links to the Proposals page.
2. **Forecast** — Browse the 18-month forecast by cost center. Use the version selector to compare current vs. prior forecast versions. Filter by category (salary, bonus, benefits, taxes). Export to CSV.
3. **Variances** — Click through months to see variances sorted by materiality. Click any row for the drill-down panel showing volume/rate decomposition.
4. **Close** — Click "Advance to Next Month" to simulate the next month. Watch actuals generate, variances calculate, and (with API key) all three agents run: detection, attribution, and proposals. A banner shows how many new proposals were created.
5. **Proposals** — Review pending forecast update proposals. Each card shows the cost center, dollar impact, rationale, and attribution detail. Accept, reject, or modify the delta before accepting. Accepted proposals create a new forecast version reflected on the Dashboard and Forecast pages.

## Architecture

```
Frontend (React :5173)  →  Backend (FastAPI :8000)  →  PostgreSQL (:5432)
                                    ↓
                            Anthropic API (Claude)
```

See [docs/architecture.md](docs/architecture.md) for the full architecture document.

## Project Structure

```
fpa-copilot/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── agents/       # AI agent classes
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic API schemas
│   │   ├── services/     # Business logic (forecast, variance calc)
│   │   ├── seed/         # Demo data generators
│   │   └── tests/        # pytest test suite
│   └── scripts/          # CLI scripts (seed, simulate, setup)
├── frontend/
│   └── src/
│       ├── pages/        # Dashboard, Forecast, Variances, Close, Proposals
│       ├── components/   # Layout, UI components
│       ├── lib/          # API client, utilities
│       └── types/        # TypeScript API types
├── docs/                 # Architecture documentation
├── SPEC.md              # Full project specification
├── RUN_LOG.md           # Build log from this run
└── DECISIONS.md         # Non-trivial decision log
```

## Testing

```bash
cd backend
python -m pytest app/tests/ -v
```

48+ tests covering: model CRUD, forecast math, simulator determinism, variance decomposition, agent output parsing (detection, attribution, proposal), proposal accept/reject/modify logic, audit trail, API endpoints.

## Roadmap

- **Run 1:** ~~Project scaffolding, data model, forecast engine, variance detection agent, UI~~ (Complete)
- **Run 2:** ~~Variance attribution agent, forecast update proposals, approval workflow UI~~ (Complete)
- **Run 3:** Monthly close report generation, commentary writing agent, one-click close demo
- **Run 4:** Auth, multi-tenant, deployment to Vercel + Railway

## License

MIT
