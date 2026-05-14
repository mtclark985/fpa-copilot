# FP&A Copilot — Run 3 Spec

**Author:** Michael Clark
**Run:** 3 of ~4
**Estimated autonomous runtime:** 4-7 hours
**Branch:** `run-3-transparency-and-simulator` (off `run-2-approval-workflow`)
**Theme:** Make it Real
**Goal of this run:** Transform the demo from "thin veneer over a black box" into something that withstands skeptical inspection. Add three things, in priority order: (1) a "Data & Assumptions" transparency layer that surfaces the company, hiring plan, forecast assumptions, and simulation events; (2) extend forecast UI visibility from 3 months to the full 18 months; (3) a read-only "What If" scenario simulator that lets the user adjust assumptions and see the forecast recalculate without committing changes. Plus a bake-in fix phase for issues surfaced during Run 2 verification.

---

## 0. Read This First — Context from Prior Runs

Run 3 builds on a working Run 2. Before writing any code:

1. **Read `RUN_LOG.md` and `DECISIONS.md`** — understand what's been built and why.
2. **Read `app/agents/base.py`** — agent base class. Note that `max_tokens` was raised to 16384 during Run 2 verification.
3. **Read `app/agents/variance_detector.py`, `variance_attributor.py`, `proposal_generator.py`** — the three agents currently in the system. Match their style if any new agent is added.
4. **Read `app/services/forecast_engine.py`** — this is the core math. The scenario simulator will reuse it, so understand its structure intimately.
5. **Read `frontend/src/pages/Variances.tsx`, `Proposals.tsx`, `Dashboard.tsx`, `Forecast.tsx`** — established UI conventions. Match them, don't invent new ones.
6. **Read `app/api/forecast.py`** — note any current limit on how many months are returned. The Run 3 forecast page visibility extension may be a small API change, a frontend filter change, or both.

**Rule:** Existing patterns win. If you're tempted to introduce a new pattern, stop and consider extending an existing one instead.

---

## 1. What We're Building

Three product threads in this run, plus one technical-debt thread.

### Thread 1: Data & Assumptions Page (the transparency layer)

A new page at `/data-and-assumptions` that lets a user inspect:

- **Company tab**: searchable, filterable table of all employees with cost center, level, location, hire date, base salary, bonus target, status (active / terminated / new hire). Sortable columns. Export to CSV.
- **Hiring Plan tab**: list of open positions with cost center, target level, target start date, status. Plus a panel listing all hires that have occurred in the simulated timeline so far, with start dates and source (planned vs. unplanned).
- **Forecast Assumptions tab**: read-only display of the assumptions baked into `forecast_engine.py`:
  - Merit cycle: % and timing
  - Attrition: annual rate, distribution method
  - Benefits load: % of base salary
  - Payroll tax: FICA rate, FICA wage base, Medicare rate
  - Bonus accrual: target % by level, payout month
  - Planned hire pace: % of headcount per quarter
  
  Each assumption is shown with its current value, a one-sentence description of what it controls, and a "where this is used" note.
- **Simulator Events tab**: chronological log of the "story variances" — the narrative events the simulator injected each month. Lets a user see *why* certain variances exist (e.g., "May: company-wide 2% COLA for Charlotte employees" appears here).

This is read-only in this run. Editing assumptions is a possible future feature, but transparency comes first.

### Thread 2: Extend Forecast Visibility

The forecast is generated 18 months forward, but the Forecast page currently only shows 3. Make the full 18-month forward forecast visible:

- Forecast table shows all 18 months by default, scrolled horizontally if needed (sticky cost-center column on the left)
- Chart on the Forecast page shows the full forward forecast
- Add a small period range selector for users who want to zoom in
- Verify the Dashboard's "FY Landing" KPI is using the full forecast, not a truncated subset

This is a focused fix, not a feature build. Whatever's currently limiting the display, find it and remove it.

### Thread 3: "What If" Scenario Simulator

A new page at `/what-if` (or a panel on the existing Forecast page — your judgment based on UX) that lets the user adjust forecast assumptions and see the result *without committing*.

Adjustable inputs (start with these — more can be added later):
- Annual attrition rate (default 12%, range 5-25%)
- Merit % (default 4%, range 0-10%)
- Benefits load % (default 18%, range 10-25%)
- Planned hire pace per quarter (default 2% of headcount, range 0-5%)
- A "headcount acceleration" multiplier: 1.0 = normal pace, 1.5 = 50% faster hiring, 0.5 = hiring freeze. Applied to all forward planned hires.

The page shows:
- Current active forecast (from real `ForecastVersion`) as a baseline line on a chart
- Scenario forecast (recalculated client-side based on the dials, or via a stateless backend endpoint) as an overlay line
- A "delta" panel showing the dollar impact: total 18-month delta, FY landing delta, breakdown by category (salary / benefits / taxes)
- A "Reset" button to return all dials to current assumption values
- A short note: "This is a scenario. Changes are not saved." — make clear nothing here affects the real forecast or generates proposals

**Critical scoping rule:** the scenario simulator is read-only and ephemeral. It does NOT:
- Persist scenarios to the database
- Generate proposals
- Affect any agent
- Create new ForecastVersions
- Touch the approval workflow

If you find yourself building anything in those directions, stop and reread this section.

### Thread 4: Run 2 Technical Debt

Fix during the dedicated phase, not scattered. Specifically:
- The "1 pre-existing failing test" mentioned in Run 2's RUN_LOG. Find it, understand it, fix or document why it's actually fine.
- Test isolation: tests should not write to the production database. Configure pytest to use a separate test database (typically a `_test` suffix). The mechanism is your choice — fixtures, conftest configuration, or an in-memory SQLite for non-Postgres-specific tests. Document the approach in DECISIONS.md.
- Defensive JSON parsing in `app/agents/base.py`: when `json.loads` fails, log the raw response and retry once with a slightly higher max_tokens before giving up. Don't silent-fail.

---

## 2. Tech Stack

No new dependencies expected. Use what Runs 1 and 2 established. If you find yourself needing a new dependency, stop and document in `BLOCKERS.md`.

---

## 3. Data Model Changes

**Minimal.** Threads 1 and 3 are mostly read-only views over existing data. Thread 4 is process, not schema.

The only candidate for a schema change is if you want to persist the simulator event log (the "story variance" narratives) as actual database rows instead of hardcoded strings in `monthly_simulator.py`. This would make Thread 1's Simulator Events tab a live database query rather than a hardcoded list. Worth doing if straightforward; skip if it adds complexity.

If you do add a `SimulatorEvent` table:
```
id: int PK
period: str
event_type: str  # e.g., 'unplanned_hire_cluster', 'cola_adjustment', 'retention_bonus_event'
narrative: str   # human-readable description
affected_cost_center_ids: JSON  # list of ints
created_at: datetime
```

Otherwise, derive the simulator events from existing data in the API layer (look at the seeded story variance constants in `monthly_simulator.py` and expose them through an endpoint).

**Lock the rest of the schema.** No changes to employees, cost centers, positions, variances, forecast lines, forecast versions, proposals, or attribution.

---

## 4. Scope: In and Out

### In scope for Run 3
- Data & Assumptions page with 4 tabs as described
- Forecast visibility extended to 18 months on Forecast page + Dashboard
- What-If scenario simulator page with the 5 dials listed
- Fix the 1 known failing test
- Test isolation: separate test database
- Defensive JSON parsing with retry in agent base class
- Navigation: add links to the new pages in the existing nav shell
- Tests for the new transparency endpoints and the what-if calculation logic

### Out of scope for Run 3
- Editable forecast assumptions (the Data & Assumptions page is read-only this run)
- Persisting "what-if" scenarios
- Generating proposals from scenario outcomes
- New agents
- Auth, multi-user, deployment (still Run 4)
- Revenue or opex forecasting (out of project scope)
- Chat interface (out of project scope)
- A close report or monthly commentary generator (deferred — may become Run 4)

### Stub or mock instead of build
- Nothing should be stubbed in this run. All threads are scoped to be fully buildable.

---

## 5. Phased Build Plan

### Phase 1: Branch setup and read-only sanity check

**Tasks:**
1. From `run-2-approval-workflow`, create branch `run-3-transparency-and-simulator` and check it out
2. Read the files listed in Section 0
3. Append a Run 3 section to `RUN_LOG.md`
4. Verify the app still works end-to-end: `docker compose up`, `uvicorn app.main:app`, `npm run dev`. Specifically verify the Run 2 approval workflow still functions (look at one proposal, accept it, see a new forecast version).
5. Commit: `chore(run-3): branch setup`

**Definition of done:**
- [ ] Branch exists and is checked out
- [ ] App runs end-to-end
- [ ] Run 2 functionality verified intact (regression check)

### Phase 2: Technical debt — failing test, test isolation, defensive parsing

This phase comes early on purpose. We're not adding features on top of latent issues.

**Tasks:**
1. Run `pytest` and identify the 1 failing test. Read it. Either fix it, or document in `DECISIONS.md` why it's safe to leave (with strong reasoning).
2. Set up test isolation:
   - Create a separate test database connection (e.g., `fpa_copilot_test`) or use SQLite in-memory for non-Postgres-specific tests
   - Configure pytest fixtures so all tests run against the isolated database
   - Tests must create their own data and tear it down — no leakage into the dev database
   - Run the full suite to confirm tests still pass and no dev data is touched
3. Update `app/agents/base.py`:
   - In `call()`, when `json.loads()` raises `JSONDecodeError`, log the raw response (truncated to a reasonable length) and retry the same call once with `max_tokens` doubled
   - If the retry also fails, raise a new exception type (e.g., `AgentOutputError`) with the raw response attached for debugging
   - Add at least one test for the retry behavior using a mocked client

**Definition of done:**
- [ ] All tests pass
- [ ] Tests run against an isolated database — verify by checking that the dev database is unchanged after a full test run
- [ ] Agent base class has retry logic and a test for it
- [ ] DECISIONS.md updated with the test-isolation approach
- [ ] Commit: `fix(phase-2): test isolation, agent retry, address failing test`

### Phase 3: Forecast visibility extension

**Tasks:**
1. Identify what's currently capping forecast display at 3 months. Likely candidates:
   - API endpoint defaulting to small `limit`
   - Frontend pagination or hardcoded slice
   - Date filter in the query
2. Update the API and frontend so the Forecast page shows all 18 months by default
3. Update the table layout: sticky cost-center column on the left, horizontal scroll for months
4. Update the Forecast page chart to show full 18-month projection
5. Add a small period range selector for zoom-in (e.g., quick filters: "Next 3 months", "Next 6 months", "Full 18 months")
6. Verify Dashboard's FY Landing KPI is using full data
7. Tests where applicable

**Definition of done:**
- [ ] Forecast page shows 18 months by default
- [ ] Cost center column is sticky on horizontal scroll
- [ ] Chart shows full forward projection
- [ ] Period range selector works
- [ ] Dashboard FY Landing reflects accepted proposals' impact across the full forward forecast
- [ ] Commit: `feat(phase-3): extend forecast visibility to 18 months`

### Phase 4: Data & Assumptions backend

**Tasks:**
1. Add endpoints under `/api/v1/transparency/` (or similar — match conventions):
   - `GET /transparency/employees` — paginated, filterable employee list
   - `GET /transparency/hiring-plan` — open positions + recent hires
   - `GET /transparency/assumptions` — current forecast assumptions, returned as structured JSON with name, value, unit, description, "used in" reference
   - `GET /transparency/simulator-events` — chronological list of injected story variances
2. The assumptions endpoint should pull values from a single source of truth (probably a module-level constants file or pydantic settings, not hardcoded inline in `forecast_engine.py`). If the assumptions are currently scattered as magic numbers, lift them into a named constants module as part of this phase. This becomes the source of truth for both `forecast_engine.py` and the new endpoint.
3. Simulator events: either query from a new `SimulatorEvent` table (if you added one — see Section 3) or expose the existing hardcoded story-variance constants from `monthly_simulator.py` via the endpoint
4. Tests for each endpoint

**Definition of done:**
- [ ] All four endpoints return well-structured JSON
- [ ] Assumptions are pulled from a single source of truth that both `forecast_engine.py` and the API endpoint reference
- [ ] Simulator events are accessible
- [ ] Tests pass
- [ ] Commit: `feat(phase-4): data and assumptions API`

### Phase 5: Data & Assumptions frontend

**Tasks:**
1. New page at `/data-and-assumptions`
2. Tab navigation for the 4 sections (use shadcn Tabs component for consistency)
3. **Company tab:**
   - TanStack Query-backed data table
   - Columns: Employee ID, Name, Cost Center, Level, Location, Hire Date, Base Salary, Status
   - Search box (filters by name or employee_number)
   - Cost center filter dropdown
   - Status filter (Active / Terminated / All)
   - Sort by any column
   - CSV export button (use existing CSV export pattern from Forecast page)
4. **Hiring Plan tab:**
   - Two sections: Open Positions, and Recent Hires (last 6 months)
   - Each as a table with relevant columns
5. **Forecast Assumptions tab:**
   - Card layout, one card per assumption category (Merit, Attrition, Benefits, Payroll Tax, Bonus, Hire Pace)
   - Each card shows: current value, unit, description, "used in" note
   - Visual: clean, scannable, low density
6. **Simulator Events tab:**
   - Chronological list, grouped by period
   - Each event shows: period, event type, narrative
7. Navigation: add "Data & Assumptions" link to the nav shell
8. Loading states, empty states, error boundaries

**Definition of done:**
- [ ] Page renders all 4 tabs cleanly
- [ ] Employee table is searchable, filterable, sortable, exportable
- [ ] Assumptions display matches the structure of the API response
- [ ] Visual quality matches existing pages
- [ ] Navigation works
- [ ] Commit: `feat(phase-5): data and assumptions page`

### Phase 6: What-If simulator backend

**Tasks:**
1. New endpoint: `POST /api/v1/what-if/run`
   - Request body: a `WhatIfScenario` object with the 5 dial values (`attrition_rate`, `merit_pct`, `benefits_load_pct`, `hire_pace_per_quarter`, `headcount_acceleration_multiplier`)
   - Response: an 18-month forecast computed using those scenario values, returned in the same shape as the regular forecast endpoint, plus a "delta" object summarizing the difference vs. the active forecast
2. **Critical:** this endpoint must reuse `forecast_engine.py`. Do NOT duplicate the forecast logic. Refactor `forecast_engine.py` if needed so it accepts assumption parameters as arguments rather than reading them from constants. The existing forecast-generation should call `forecast_engine.compute(default_assumptions)` and the scenario should call `forecast_engine.compute(scenario_assumptions)`. Same code, different parameters.
3. Endpoint is stateless: no database writes, no records persisted
4. Tests:
   - Default scenario (all dials at current values) produces a forecast equal to the active forecast within rounding tolerance
   - Bumping attrition higher should reduce total comp expense
   - Bumping hire_pace higher should increase total comp expense
   - Headcount acceleration of 0.5 (freeze) should reduce expense vs. 1.0

**Definition of done:**
- [ ] Endpoint works
- [ ] `forecast_engine.py` is parameterized (no longer reads assumptions from module-level constants directly)
- [ ] All forecast generation code paths (initial seed, scenario, future proposal flow) go through the same `compute()` function
- [ ] Tests pass and prove the math behaves correctly under different scenarios
- [ ] Commit: `feat(phase-6): what-if scenario calculation engine`

### Phase 7: What-If simulator frontend

**Tasks:**
1. New page at `/what-if`
2. Layout: left panel with the 5 dials (use shadcn Slider components), right panel with the chart and delta breakdown
3. Each dial has:
   - Label, current default value, min/max range, unit
   - Visible numeric value updating live as user drags
   - "Reset to default" button
4. Chart shows two lines: Active Forecast (baseline) and Scenario Forecast (overlay)
5. Below chart: "Delta vs. Active Forecast" panel with:
   - Total 18-month dollar impact
   - FY Landing impact
   - Category breakdown (salary, benefits, taxes)
6. Debounce dial inputs so we don't spam the backend with every pixel of drag movement (500ms debounce)
7. Persistent banner: "This is a scenario. Changes are not saved and do not affect proposals or the active forecast."
8. "Reset All" button to return everything to defaults
9. Loading state while the scenario is recalculating
10. Navigation: add "What If" link to nav shell

**Definition of done:**
- [ ] Page renders with all 5 dials
- [ ] Adjusting a dial recalculates the scenario forecast and updates the chart
- [ ] Delta panel shows correct numbers
- [ ] Debounce prevents request flood
- [ ] Banner is visible and clear
- [ ] Reset works
- [ ] Commit: `feat(phase-7): what-if scenario simulator page`

### Phase 8: Polish, docs, demo verification

**Tasks:**
1. Run the full demo flow end-to-end and identify any rough edges:
   - Open Dashboard → see real KPIs and forecast
   - Open Data & Assumptions → click through all 4 tabs, look at the underlying data
   - Open Forecast → see all 18 months, scroll horizontally
   - Open What-If → adjust attrition higher, see forecast drop, reset
   - Open Variances → review a high-severity variance with agent reasoning
   - Open Proposals → review a pending proposal, modify-and-accept it
   - Open Dashboard → verify FY Landing changed to reflect the accepted proposal
2. Fix any rough edges found
3. Update `README.md`:
   - Add Run 3 section to the feature list
   - Update the demo script to walk through the new pages
4. Update `docs/architecture.md` to reflect new endpoints and the assumptions-as-parameters refactor
5. Update `DECISIONS.md` with key Run 3 calls (test isolation approach, scenario stateless design, etc.)
6. Final RUN_LOG.md entry summarizing Run 3
7. All tests passing, no console errors, no `[WIP]` commits

**Definition of done:**
- [ ] Full end-to-end demo works smoothly
- [ ] Documentation reflects Run 3 changes
- [ ] Commit: `docs(phase-8): run 3 polish and documentation`

---

## 6. Working Agreements (Run 3 — note differences from Run 2)

**Branching:** all commits on `run-3-transparency-and-simulator`. Do NOT push to main. Do NOT merge to main. Do NOT merge to `run-2-approval-workflow`. Michael will review and merge manually.

**Commit policy:** same as prior runs.

**Logging:** append Run 3 section to existing RUN_LOG.md. Do not overwrite prior runs.

**When to stop and wait for human:**
- Any task requiring `ANTHROPIC_API_KEY` if not set
- Any breaking change to existing endpoints used by the Variances or Proposals pages
- Any schema change beyond what's described in Section 3
- If the test isolation work surfaces fundamental issues with how tests are structured — stop and document, don't reinvent
- If the `forecast_engine.py` refactor (Phase 6) reveals the engine has implicit dependencies that make parameterization hard — stop and document the situation before making invasive changes
- Same general triggers as prior runs

**When NOT to stop:**
- Same as prior runs
- Plus: lint, type, or test errors from your own new code — fix them
- Plus: inconsistencies between spec and existing code — existing code wins, document the choice

**Decision log:** every non-trivial call (test isolation mechanism, assumption-constants module location, scenario UI layout choices) goes in DECISIONS.md with rationale.

**Real-data integration test:** the agent retry logic in Phase 2 should have at least one test that does NOT use a mocked Anthropic client — it should make a real API call against a small fixture variance and confirm the retry behavior works end-to-end. This is one place where mocked-only testing has hidden problems in past runs.

---

## 7. Environment

`.env` unchanged. ANTHROPIC_API_KEY required. Docker Postgres running.

---

## 8. Definition of Done for Run 3

The run is successful when all of the following are true:
- [ ] All 8 phases complete on branch `run-3-transparency-and-simulator`
- [ ] Branch has clean commit history
- [ ] App runs end-to-end with all Run 1, Run 2, and Run 3 functionality working
- [ ] No regression in existing Variances, Proposals, Dashboard, Forecast, or Close pages
- [ ] Data & Assumptions page exists with all 4 tabs functional
- [ ] Forecast page shows full 18-month forward forecast
- [ ] What-If simulator page exists and recalculates the forecast based on dial inputs
- [ ] All tests passing against an isolated test database (dev database is untouched after a test run)
- [ ] Agent base class has retry logic and a real-API integration test
- [ ] `forecast_engine.py` accepts assumptions as parameters (no module-level magic numbers)
- [ ] Documentation updated

---

## Starting Prompt for Claude Code

Paste this verbatim into Claude Code:

```
Read SPEC.md in full before doing anything else. Then read the files listed in
Section 0 of the spec. Confirm you understand the architecture from Runs 1 and 2
and the goal of Run 3.

This is a Run 3 spec. The codebase already has working code from Runs 1 and 2.
You must integrate with existing patterns, not invent parallel ones. When in
doubt, match what's already there.

Create the branch `run-3-transparency-and-simulator` from `run-2-approval-workflow`.
All commits go on the new branch. Do NOT push to main or to run-2-approval-workflow.

Execute Phases 1 through 8 in order. For each phase:
1. Read the phase tasks
2. Implement them
3. Run tests
4. If everything in the phase's Definition of Done is satisfied, commit on the
   feature branch with the format specified
5. Append an entry to RUN_LOG.md describing what was done
6. Move to the next phase

Follow the "when to stop" rules in Section 6 strictly. Stop only for the listed
reasons, document in RUN_LOG.md, and wait.

Start with Phase 1, Task 1. Go.
```