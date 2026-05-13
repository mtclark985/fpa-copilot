# Architecture — FP&A Copilot

## System Overview

```
                    ┌──────────────┐
                    │   Frontend   │
                    │  React + TS  │
                    │  Vite :5173  │
                    └──────┬───────┘
                           │ HTTP/JSON
                    ┌──────▼───────┐
                    │   Backend    │
                    │   FastAPI    │
                    │  Uvicorn     │
                    │   :8000     │
                    └──┬───────┬───┘
                       │       │
              ┌────────▼──┐ ┌──▼──────────┐
              │ PostgreSQL │ │  Anthropic  │
              │    :5432   │ │    API      │
              │  (Docker)  │ │ (Claude)    │
              └────────────┘ └─────────────┘
```

## Backend Architecture

### Layers

1. **API Layer** (`app/api/`) — FastAPI routers defining REST endpoints. Thin layer that delegates to services and agents.

2. **Services Layer** (`app/services/`) — Business logic. The forecast engine, actuals ingestion, and variance calculator live here. No framework dependencies.

3. **Agents Layer** (`app/agents/`) — AI agent classes that wrap Anthropic API calls. Each agent has a single responsibility, returns Pydantic models, and logs every call.

4. **Models Layer** (`app/models/`) — SQLAlchemy 2.0 ORM models with async support. Relationships use `selectin` loading for async compatibility.

5. **Seed Layer** (`app/seed/`) — Demo data generators. Company generator and monthly simulator. Deterministic via fixed random seeds.

### Key Design Decisions

- **No agent framework**: Agents are plain Python classes wrapping the Anthropic SDK. This keeps the code simple, debuggable, and framework-independent.

- **Async throughout**: FastAPI + SQLAlchemy async + asyncpg. Agent calls are I/O-bound, so async lets the server handle concurrent requests without blocking.

- **Single active forecast**: The `is_active` flag on ForecastVersion ensures exactly one forecast is "current" at any time. Future runs will add the approval workflow to create new versions.

- **Variance decomposition**: Every variance is decomposed into volume (headcount delta × forecast rate) and rate (actual headcount × rate delta). This gives FP&A analysts the "why" behind the numbers.

- **Materiality scoring**: A 0-100 composite score combining absolute dollar size (40%), percentage variance (30%), and unexpectedness (30%). Material threshold is 60.

## Data Flow

### Seed / Setup Flow
```
seed_company.py → 500 employees, 31 cost centers, ~28 open positions
                ↓
forecast_engine.py → 18-month forecast (salary, bonus, benefits, taxes)
                ↓
simulate_month.py × 6 → Payroll actuals with intentional variances
                ↓
variance_calculator.py → Volume/rate decomposition + materiality scoring
```

### Monthly Close Flow (Runtime)
```
POST /close/advance-month
    → simulate_month (generate actuals, apply story variance)
    → calculate_variances (forecast vs actual decomposition)
    → VarianceDetectorAgent (AI assessment of each material variance)
    → Response with summary
```

## Database Schema

```
cost_centers ─┬── employees ─── actuals
              ├── positions
              ├── forecast_lines ─── forecast_versions
              └── variances ─────── forecast_versions
```

- **cost_centers**: 3-level hierarchy (Division > Department > Team)
- **employees**: Active/terminated headcount with comp details
- **positions**: Open slots for headcount planning
- **forecast_versions / forecast_lines**: Versioned forecast at CC × month × category
- **actuals**: Employee-level payroll actuals
- **variances**: Calculated variances with optional agent assessment fields

## Frontend Architecture

- **React 18** with TypeScript strict mode
- **TanStack Query** for server state management (stale-while-revalidate caching)
- **React Router** for client-side routing
- **Tailwind CSS** for utility-first styling
- **Recharts** for the actual-vs-forecast chart
- Pages: Dashboard, Forecast, Variances, Close

## API Contracts

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/employees` | List employees |
| GET | `/api/v1/cost-centers` | List cost centers |
| GET | `/api/v1/forecast` | Get active forecast |
| GET | `/api/v1/actuals` | Get actuals by period |
| GET | `/api/v1/variances` | Get variances (filterable) |
| GET | `/api/v1/variances/{id}` | Single variance detail |
| POST | `/api/v1/variances/{period}/calculate` | Recalculate variances |
| POST | `/api/v1/variances/{period}/analyze` | Run AI agent analysis |
| POST | `/api/v1/close/advance-month` | Full monthly close cycle |
| GET | `/api/v1/kpis/dashboard` | Dashboard KPIs |
