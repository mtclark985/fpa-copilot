# Decisions Log — Run 1

## D1: Python 3.14 compatibility
**Phase 1** — The system has Python 3.14.4 installed (spec says 3.11+). Added `setuptools` as build backend in pyproject.toml since pip's editable install requires it. All dependencies (SQLAlchemy, FastAPI, asyncpg, etc.) work fine on 3.14.

## D2: Tailwind CSS v4 via @tailwindcss/vite
**Phase 1** — Used Tailwind CSS v4 with the Vite plugin (`@tailwindcss/vite`) instead of the PostCSS-based v3 approach. v4 is the current latest and provides better Vite integration. No `tailwind.config.js` file needed — configuration is done via CSS `@theme` directive.

## D3: 31 cost centers instead of 20
**Phase 3** — The spec says "20 cost centers" but a realistic 3-level hierarchy (4 divisions, 11 departments, 16 teams) produces 31. The teams are the leaf-level cost centers where employees sit. This gives richer variance data. Employees are distributed only to team-level cost centers.

## D4: Naive datetimes for database defaults
**Phase 2** — Used `datetime.datetime.utcnow` (naive) instead of timezone-aware datetimes for `created_at` / `detected_at` defaults. asyncpg with PostgreSQL's `TIMESTAMP WITHOUT TIME ZONE` column type throws errors when mixing offset-aware and offset-naive datetimes. Since this is a single-timezone demo app, naive UTC is fine.

## D5: Agent uses synchronous Anthropic client
**Phase 7** — The Agent base class uses the synchronous `anthropic.Anthropic` client rather than the async variant. The async client adds event loop complexity with minimal benefit for single API calls. FastAPI runs the sync call in a threadpool automatically.

## D6: Forecast includes all-in comp cost
**Phase 4** — Year 1 forecast totals ~$101M for 500 employees ($73M salary + $10M bonus + $13M benefits + $5M taxes). This is the all-in loaded cost, not just salary. The spec's "$60-80M" likely referred to base salary alone.

## D7: Agent tests use mocked Anthropic responses
**Phase 7** — Agent tests use `unittest.mock.patch` to mock the Anthropic SDK rather than making real API calls. This avoids burning tokens in tests and makes tests deterministic. The agent can be run live via the API endpoint once `ANTHROPIC_API_KEY` is set.

## D8: Test isolation via unique keys
**Phase 7** — Model tests use UUID-based unique codes/numbers (`TEST-{uuid}`) to avoid conflicts with seeded data in the shared Postgres database. This is simpler than a fully isolated test database while still providing reliable test results.

---

# Decisions Log — Run 2

## D9: Materiality threshold for attribution
**Phase 3** — Attribution agent processes variances with materiality_score >= 50 (vs. the detector's threshold of 30). This focuses attribution effort on truly material variances while the detector casts a wider net for assessment.

## D10: Idempotent agent runs
**Phases 3-4** — Both new agents check for existing records before creating new ones. The attribution agent skips already-attributed variance IDs; the proposal agent skips periods with existing proposals. This makes the advance-month chain safely re-runnable.

## D11: Forecast version cloning on accept
**Phase 6** — Accepting a proposal copies ALL forecast lines from the active version to a new version, applying the delta only to matching CC×category×period lines. This ensures a clean snapshot and no orphan references. The trade-off is more rows in forecast_lines, but correctness is worth it for a 500-employee company.

## D12: Alembic version stamp
**Phase 2** — The database had existing tables from Run 1's setup_demo.py (which uses Base.metadata.create_all) but no alembic_version entry. Stamped the DB at the initial migration revision before generating the Run 2 migration. This is a one-time fix.

## D13: Pre-existing test failure (7 months)
**Phase 1** — `test_six_months_of_actuals` fails with 7 == 6 because a 7th month was advanced during manual testing. This is pre-existing state in the shared database, not a regression. All Run 2 changes are validated by the other 48 passing tests.

---

# Decisions Log — Run 3

## D14: Test isolation via separate Postgres database
**Phase 2** — Tests now run against `fpa_copilot_test` (separate Postgres database), not the dev database. The conftest.py session-scoped fixture auto-creates the test DB if it doesn't exist, drops and recreates all tables, then seeds data (company generator + forecast engine + 6 months of simulator + variance calculation). Each test gets a fresh engine/session to avoid asyncpg "operation in progress" conflicts. This fixes the `test_six_months_of_actuals` failure since the test DB has exactly 6 months of controlled data.

## D15: Agent retry with AgentOutputError
**Phase 2** — The agent base class now retries once with doubled `max_tokens` when JSON parsing fails. This handles the most common failure mode (truncated JSON output). If both attempts fail, an `AgentOutputError` is raised with the raw response attached for debugging. The `_make_api_call` method was extracted for reuse between first attempt and retry.

## D16: Real-API agent retry test skipped
**Phase 2** — The spec requests a real-API integration test for agent retry. Skipped because `ANTHROPIC_API_KEY` is not set. The retry behavior is covered by 4 mocked tests. When the API key is available, a live test can be added.
