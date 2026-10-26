# FP&A Copilot — Run 2 Spec

**Author:** Michael Clark
**Run:** 2 of ~4
**Estimated autonomous runtime:** 4-8 hours
**Branch:** `run-2-approval-workflow` (do not commit to main)
**Goal of this run:** Add the approval workflow — the core differentiator of this product. Two new agents (Variance Attribution + Forecast Update Proposal) and a UI flow that lets a human accept, reject, or modify proposed forecast changes. By the end of this run, the killer demo is real: hit "Advance Month," watch the system surface variances, attribute them to drivers, propose forward-looking forecast updates, and present them as approvable cards.

---

## 0. Read This First — How Run 2 Differs from Run 1

Run 2 is **not greenfield**. The codebase has working conventions and you must respect them. Before writing any code, read the following and let what's already there guide your choices:

1. **Read `RUN_LOG.md` and `DECISIONS.md`** from Run 1. Understand the architecture and the rationale.
2. **Read `app/agents/base.py`** — extend this pattern, do not introduce a parallel one.
3. **Read `app/agents/variance_detector.py`** — your new agents should match this style (SYSTEM_PROMPT constant, Pydantic output models, `analyze_period`-style method that takes a session, uses `await self.call(...)`, and persists results back to the database).
4. **Read `app/services/variance_calculator.py`** — your new services should match this style.
5. **Read `app/api/variances.py`** — your new endpoints should match this REST style.
6. **Read `frontend/src/pages/Variances.tsx`** — match the UI patterns, component conventions, TanStack Query usage, and shadcn component choices.
7. **Read `frontend/src/lib/api.ts`** — extend this client, do not create a parallel one.

**Rule:** If you find yourself about to invent a new pattern, stop and check whether an existing pattern already covers it. Consistency with Run 1 is more important than your local opinion on the better way.

---

## 1. What We're Building

In Run 1, when actuals arrive, the system calculates variances and the Variance Detection Agent labels them with severity and a one-sentence rationale. That's diagnostic. It tells you what happened.

Run 2 makes the system *prescriptive*:

- **Variance Attribution Agent**: For each material variance, traces it to specific drivers (a particular hire, a particular departure, a comp adjustment) — not just "headcount accelerated" but "Risk team filled positions REQ-1041 and REQ-1052 in January, 60 days ahead of plan."
- **Forecast Update Proposal Agent**: Given the attribution, reasons forward: "If Risk hires landed early, the forward headcount run-rate is now elevated; we should increase the Risk salary forecast by $X per month for the rest of the year." Outputs structured proposals.
- **Approval UI**: Each proposal appears as a card with rationale, dollar impact, accept/reject/modify controls. Accepted proposals generate a new `ForecastVersion` with the changes applied. Full audit trail.

End-to-end demo flow after Run 2:
1. User hits "Advance to Next Month" on Close page
2. System ingests actuals → calculates variances → runs Detection Agent (existing, unchanged)
3. System runs Attribution Agent (new) → links variances to specific employees/positions/events
4. System runs Proposal Agent (new) → generates forecast update proposals
5. UI shows new "Proposals" page with cards
6. User reviews each proposal: accept, reject, or modify the dollar impact
7. On accept, a new ForecastVersion is created with the change applied; the old version is archived; the dashboard reflects the new forward forecast

---

## 2. Tech Stack

No new dependencies expected. Use what Run 1 already established:
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, anthropic SDK
- Frontend: React 18, Vite, TypeScript, Tailwind, shadcn/ui, TanStack Query, Recharts
- Database: PostgreSQL 16
- Agent model: `claude-haiku-4-5` (matches base.py)

If you find yourself needing a new dependency, stop and document in `BLOCKERS.md` before installing.

---

## 3. Data Model Changes

New tables. Add via Alembic migration, not by editing models retroactively.

### `ForecastProposal`
A specific change to the forecast, proposed by an agent, awaiting human decision.

```
id: int PK
created_at: datetime
created_for_period: str  # the close period that generated this proposal (e.g., "2026-06")
status: str  # 'pending' | 'accepted' | 'rejected' | 'modified_and_accepted' | 'superseded'

# What's being proposed
cost_center_id: int FK
category: str  # 'salary' | 'bonus' | 'benefits' | 'taxes' | 'other'
affected_periods: JSON  # list of "YYYY-MM" strings the change applies to, e.g. ["2026-07", "2026-08", ..., "2027-12"]
delta_per_period: numeric  # dollar amount to add to each affected period

# Why
agent_rationale: str  # full reasoning from the proposal agent
driving_variance_ids: JSON  # list of Variance.id values that motivated this proposal
attributed_events: JSON  # structured events from the attribution agent (see below)
confidence: str  # 'high' | 'medium' | 'low'

# Decision metadata (populated when status changes)
decided_at: datetime nullable
decided_by: str nullable  # placeholder for future auth; "system" or "user" for now
decision_note: str nullable  # user-provided note on accept/reject/modify
modified_delta_per_period: numeric nullable  # if user modified the amount before accepting

# Linkage to applied ForecastVersion (populated on accept)
resulting_forecast_version_id: int FK nullable
```

### `AttributionRecord`
Structured output from the Variance Attribution Agent. One per material variance that the agent could attribute.

```
id: int PK
variance_id: int FK
created_at: datetime
attribution_type: str  # 'early_hire' | 'late_hire' | 'unplanned_hire' | 'unplanned_departure' | 'comp_adjustment' | 'bonus_event' | 'other'
narrative: str  # one-paragraph natural language explanation
structured_drivers: JSON  # e.g. [{"type": "hire", "employee_id": 412, "expected_start": "2026-03-01", "actual_start": "2026-01-15"}, ...]
confidence: str  # 'high' | 'medium' | 'low'
```

### `ProposalDecisionAudit`
Append-only log of every decision made on a proposal. One row per state change. Even though the proposal itself stores its current status, this gives us a clean audit trail.

```
id: int PK
proposal_id: int FK
occurred_at: datetime
from_status: str
to_status: str
note: str nullable
delta_change: numeric nullable  # if modified, the difference between original and final
```

### Existing tables — minimal changes
- `ForecastVersion`: add `parent_version_id` FK nullable (so accepted proposals can chain new versions to old ones)
- `ForecastVersion`: add `source` str column: 'initial_plan' | 'proposal_accepted' | 'manual' — describes how this version was created

That's it. **Do not add other columns** to existing tables. If you think you need more, stop and document in `DECISIONS.md`.

---

## 4. Scope: What's In and What's Out

### In scope for Run 2
- Two new agents: Attribution + Proposal, following the Run 1 agent base class pattern
- New API endpoints to trigger them, fetch proposals, and act on them
- Hook into the existing `POST /api/v1/close/advance-month` flow so the new agents run automatically after variance detection
- Frontend: new "Proposals" page with card-based approval UI, plus integration with the existing Close page flow
- Alembic migration for the new tables and ForecastVersion columns
- Forecast versioning: accepting a proposal creates a new active ForecastVersion that diffs from the prior version
- Dashboard updates so the active forecast line reflects accepted proposals
- Tests on the new logic (agent output validation, proposal acceptance creates correct version, modification math is correct)

### Out of scope for Run 2
- Auth / multi-user (still deferred to Run 4)
- Bulk accept/reject (one-at-a-time approval only)
- Undoing an accepted proposal (one-way for now)
- Commentary generation for monthly close report (Run 3)
- Editing proposal *rationale* or *affected periods* — user can only modify the dollar delta in this run
- Cross-cost-center proposals (every proposal targets exactly one cost center × one category × N periods)

### Stub or mock instead of build
- Authorship: `decided_by` field gets the string `"user"` when accepted/rejected via UI, `"system"` for any automatic actions

---

## 5. Phased Build Plan

### Phase 1: Branch setup and Run 2 working agreements

**Goal:** Create the feature branch and read the existing codebase before any new code.

**Tasks:**
1. From main (which should currently be at the Run 1 final commit + the model/prompt fix from the morning of 2026-05-13), create branch `run-2-approval-workflow` and check it out
2. Read the files listed in Section 0
3. Create `RUN_LOG.md` entries section for Run 2 (do not overwrite Run 1's entries; append)
4. Confirm `docker compose up`, `python scripts/setup_demo.py`, and `npm run dev` still work end-to-end before changing anything
5. Initial commit on the branch: `chore(run-2): branch setup`

**Definition of done:**
- [ ] Branch exists, currently checked out
- [ ] App still runs end-to-end (don't break Run 1)
- [ ] RUN_LOG.md has a Run 2 section started

### Phase 2: Data model migration

**Goal:** New tables and ForecastVersion columns.

**Tasks:**
1. Add SQLAlchemy models: `ForecastProposal`, `AttributionRecord`, `ProposalDecisionAudit`
2. Add columns to `ForecastVersion`: `parent_version_id`, `source`
3. Generate Alembic migration
4. Apply migration: `alembic upgrade head`
5. Confirm: existing data still loads, new tables exist and are queryable, existing tests still pass
6. Write 3-5 unit tests covering create/query of new models

**Definition of done:**
- [ ] Migration applies cleanly to existing database with Run 1 data still present
- [ ] All Run 1 tests still pass
- [ ] New model tests pass
- [ ] Commit: `feat(phase-2): data model for proposals and attribution`

### Phase 3: Variance Attribution Agent

**Goal:** New agent that takes material variances for a period and produces `AttributionRecord` rows linking variances to specific events.

**Tasks:**
1. Build `app/agents/variance_attributor.py` following the pattern of `variance_detector.py`
2. Agent input context should include:
   - The material variances for the period (severity >= medium from the detector, or materiality_score >= 50)
   - The list of hires that occurred in the period vs. planned hires
   - The list of departures that occurred in the period
   - Any open positions in the affected cost center
   - Salary changes in the period (e.g., off-cycle adjustments)
3. Agent SYSTEM_PROMPT should make clear:
   - Job: link each variance to specific structured drivers
   - Output: an AttributionRecord per variance with attribution_type, narrative, structured_drivers, confidence
   - Be specific (real employee IDs, real position numbers) not vague
4. Pydantic output schema mirrors the database structure
5. Persist `AttributionRecord` rows on completion
6. Add endpoint `POST /api/v1/attribution/{period}/run`
7. Tests using mocked Anthropic responses

**Definition of done:**
- [ ] Agent runs against real Run 1 seeded data and produces attributions for at least 70% of material variances
- [ ] Attributions reference real employee_ids / position_ids that exist in the database
- [ ] Endpoint works and persists records
- [ ] Tests pass
- [ ] Commit: `feat(phase-3): variance attribution agent`

### Phase 4: Forecast Update Proposal Agent

**Goal:** New agent that takes attribution records and produces `ForecastProposal` rows.

**Tasks:**
1. Build `app/agents/proposal_generator.py`
2. Agent input context:
   - Attribution records for the period
   - Current active forecast (next 12 months by cost center × category)
   - Any prior proposals already accepted in this cost center (don't double-propose)
3. Agent SYSTEM_PROMPT should:
   - Frame the task: "you decide which attributed variances reflect structural changes worth updating the forecast for, vs. one-time events to ignore"
   - Be explicit that not every variance becomes a proposal — one-time events should NOT generate a forward-looking proposal
   - For each proposal, output: which cost center, which category, which periods, dollar delta per period, rationale, confidence, and which driving_variance_ids motivated it
4. Pydantic output schema: a list of `ProposalCandidate` objects
5. Persist as `ForecastProposal` rows with status='pending'
6. Add endpoint `POST /api/v1/proposals/{period}/generate`
7. Tests

**Key design rule:** the proposal agent should be conservative. A bias toward fewer, better-justified proposals over many speculative ones. The agent should be willing to say "no proposals warranted" for a quiet month.

**Definition of done:**
- [ ] Agent runs and produces 0-10 proposals per period (not 50+)
- [ ] Each proposal references real driving_variance_ids
- [ ] Quiet months produce few proposals; eventful months (e.g., the May COLA, the Risk hiring acceleration) produce specific proposals tied to those events
- [ ] Endpoint persists proposals
- [ ] Tests pass
- [ ] Commit: `feat(phase-4): forecast update proposal agent`

### Phase 5: Wire new agents into close flow

**Goal:** Make the existing `POST /api/v1/close/advance-month` endpoint chain through the new agents automatically.

**Tasks:**
1. Update the advance-month endpoint to call (in order): simulate month → calculate variances → run detection agent → run attribution agent → run proposal agent
2. Each step should be idempotent (re-runnable without duplicates)
3. Add logging at each step
4. Update tests for the close flow
5. Run the chain against the 6 already-seeded months: regenerate detection assessments (already exist, no-op), generate attribution records, generate proposals
6. Verify proposal count is sensible across the 6 months (probably 8-25 total proposals)

**Definition of done:**
- [ ] One API call drives the full chain
- [ ] Re-running the chain doesn't create duplicate records
- [ ] All 6 seeded months have attribution + proposals after running
- [ ] Tests pass
- [ ] Commit: `feat(phase-5): chain attribution and proposals into close flow`

### Phase 6: Proposal endpoints (CRUD + decisions)

**Goal:** API surface for the UI to read proposals and take actions.

**Endpoints:**
- `GET /api/v1/proposals` — list, filterable by status (`?status=pending`), period, cost_center
- `GET /api/v1/proposals/{id}` — full detail including attribution records and driving variances
- `POST /api/v1/proposals/{id}/accept` — body optional `{"note": "..."}`; creates new ForecastVersion, updates proposal status to 'accepted'
- `POST /api/v1/proposals/{id}/reject` — body optional `{"note": "..."}`; status to 'rejected'
- `POST /api/v1/proposals/{id}/modify-and-accept` — body `{"modified_delta_per_period": <number>, "note": "..."}`; same as accept but applies the modified delta and status is 'modified_and_accepted'

**Forecast version creation on accept:**
1. Clone the current active ForecastVersion (copy all ForecastLine rows)
2. Apply the delta from the proposal to the matching cost_center × category × affected_periods
3. Set old version `is_active=false`, new version `is_active=true`
4. Set new version `parent_version_id = old.id`, `source = 'proposal_accepted'`
5. Set `resulting_forecast_version_id` on the proposal
6. Append a `ProposalDecisionAudit` row

**Definition of done:**
- [ ] All five endpoints work
- [ ] Accepting a proposal: new forecast version exists, is active, has the delta applied to the right lines
- [ ] Rejecting a proposal: status changes, no forecast version created
- [ ] Modify-and-accept: forecast version uses the modified delta, audit captures both original and final
- [ ] Tests for each endpoint covering happy path and basic error cases
- [ ] Commit: `feat(phase-6): proposal CRUD and decision endpoints`

### Phase 7: Proposals page (frontend)

**Goal:** New page listing pending proposals as cards, with full detail and accept/reject/modify controls.

**Tasks:**
1. Add `Proposals` page at `/proposals` route
2. Add navigation link in the existing nav shell
3. Top of page: filter chips (Pending / Accepted / Rejected / All) and a period selector
4. Card layout for each proposal showing:
   - Header: cost center name, category, period range
   - Dollar impact: total delta and per-period delta with clear sign (+/- coloring)
   - Confidence badge
   - Agent rationale (full text)
   - Expandable section "Driving variances" → shows variance line items
   - Expandable section "Attribution detail" → shows attribution narrative and structured drivers
   - Action buttons: Accept (green), Reject (red), Modify (neutral)
5. Modify flow: clicking Modify opens an inline numeric input prefilled with the proposed delta; user changes it; Confirm button becomes "Accept Modified"
6. Accept / Reject / Confirm flows all open an optional note field, then call the API and refresh the list
7. After action: show a toast, the card moves out of "Pending" (or is filtered out)
8. Empty state when no pending proposals: a clean message and a "Run analysis for [period]" CTA

**Definition of done:**
- [ ] Page loads, lists pending proposals
- [ ] Each card renders all fields properly with clean styling consistent with existing pages
- [ ] Accept, Reject, and Modify-and-Accept all work end-to-end
- [ ] After action, list updates correctly
- [ ] Empty state and error states handled
- [ ] No console errors
- [ ] Commit: `feat(phase-7): proposals page with approval workflow`

### Phase 8: Dashboard and Forecast page integration

**Goal:** Make the rest of the app reflect accepted proposals.

**Tasks:**
1. The Dashboard "FY Landing" KPI and the actual-vs-forecast chart should pull from the active ForecastVersion (which now reflects accepted proposals)
2. Add a small "Active Forecast: [name] (v[number], updated MMM DD)" indicator to the dashboard so you can see when the forecast has changed
3. Forecast page: add a version selector at the top so user can view prior versions
4. Add a "Forecast History" section to the Dashboard or its own small page: list of forecast versions with source ("Initial Plan" / "Proposal Accepted: ...") and timestamps
5. Close page: after advancing a month, surface a new banner "N new proposals awaiting your review" with a button to jump to Proposals page

**Definition of done:**
- [ ] Dashboard reflects active version
- [ ] Forecast page can show prior versions
- [ ] Close page surfaces new-proposals notice
- [ ] Commit: `feat(phase-8): dashboard and forecast integration with versioned forecasts`

### Phase 9: Polish and demo flow verification

**Goal:** Tighten loose ends, verify the killer demo flow works end-to-end, update docs.

**Tasks:**
1. Reset and reseed the database; run all 6 months through the full chain
2. Verify the demo script: open dashboard → advance to a new month (say, simulate "2026-07") → wait → see new variances + attributions + proposals → go to Proposals page → review a proposal → modify and accept → return to dashboard → see forecast changed
3. Update `README.md` Run 2 section: describe the approval workflow, add it to the demo script section
4. Update `docs/architecture.md` to include the new agents and proposal flow
5. Update `DECISIONS.md` with any non-trivial calls made during Run 2
6. Ensure `RUN_LOG.md` is comprehensive for Run 2

**Definition of done:**
- [ ] Full demo flow works in one session without manual intervention beyond clicks
- [ ] Documentation updated
- [ ] All tests passing
- [ ] No `[WIP]` commits
- [ ] Commit: `docs(phase-9): run 2 documentation and polish`

---

## 6. Working Agreements (Run 2 — note differences from Run 1)

**Commit policy:** same as Run 1. Conventional commits, one per phase minimum, more granular OK.

**Logging policy:** append Run 2 entries to RUN_LOG.md. Do not overwrite Run 1 entries.

**Branching:** all commits on `run-2-approval-workflow`. Do NOT push to main. Do NOT merge to main. Michael will review and merge manually.

**When to stop and wait for human:**
- Same triggers as Run 1
- Plus: any change that would break a Run 1 endpoint or schema relationship (e.g., renaming a column on an existing table) — stop and document
- Plus: if the attribution or proposal agent's output quality looks weak on the first real run (e.g., proposals reference non-existent employees, attributions are generic) — stop, document the issue in RUN_LOG.md, and wait for human review of the prompt
- Plus: if proposal count for a quiet month exceeds 15 or for the seeded months exceeds 40 total — the agent is over-proposing; stop and let human tune the prompt

**When NOT to stop:**
- Same as Run 1
- Plus: any inconsistency between the spec and the existing codebase that can be resolved by matching the existing codebase. The existing codebase wins.

**Decision log:** every non-trivial choice that integrates with existing code (which patterns to follow, how to handle edge cases in the proposal logic) goes in DECISIONS.md with rationale.

---

## 7. Environment

`.env` is unchanged from Run 1. ANTHROPIC_API_KEY must be set. Docker Postgres must be running.

---

## 8. Definition of Done for Run 2

The run is successful when all of the following are true:
- [ ] All 9 phases complete on branch `run-2-approval-workflow`
- [ ] Branch has clean commit history
- [ ] App runs end-to-end: docker → backend → frontend → full demo flow works
- [ ] All Run 1 functionality still works (regression check)
- [ ] Variance Attribution Agent produces high-quality attributions tied to real employees/positions
- [ ] Forecast Update Proposal Agent produces a sensible number of well-justified proposals (not over-proposing)
- [ ] Approval UI lets a user accept, reject, or modify-and-accept proposals
- [ ] Accepting a proposal creates a new ForecastVersion and the dashboard reflects it
- [ ] All tests passing
- [ ] Documentation updated

---

## Starting Prompt for Claude Code

Paste this verbatim into Claude Code when kicking off the run:

```
Read SPEC.md in full before doing anything else. Then read the files listed in
Section 0 of the spec. Confirm you understand the architecture from Run 1 and
the goal of Run 2.

This is a Run 2 spec. The codebase already has working code from Run 1. You
must integrate with existing patterns, not invent parallel ones. When in doubt,
match what's already there.

Create the branch `run-2-approval-workflow` from main. All commits go on the
branch. Do NOT push to main. Do NOT merge to main.

Execute Phases 1 through 9 in order. For each phase:
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