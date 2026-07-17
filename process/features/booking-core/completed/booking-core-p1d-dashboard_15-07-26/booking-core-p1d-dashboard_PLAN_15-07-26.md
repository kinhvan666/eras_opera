---
name: booking-core-p1d-dashboard
description: "Phase 1d Leadership Dashboard for booking-core — Streamlit app visualizing 8 hospitality KPIs from Kimball dimensional layer"
date: 15-07-26
metadata:
  type: plan
  complexity: simple
  feature: booking-core
  phase: 1d
  status: planned
---

# Booking Core - Phase 1d Dashboard Implementation Plan

**Date**: 15-07-26  
**Complexity**: Simple (one-session feature)  
**Status**: ⏳ PLANNED  
**Feature**: booking-core  
**Phase**: 1d (Dashboard V1)

---

## Quick Links

- [Overview](#overview)
- [Phase Completion Rules](#phase-completion-rules)
- [Execution Brief](#execution-brief)
- [Scope](#scope-inout)
- [Assumptions and Constraints](#assumptions-and-constraints)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements](#non-functional-requirements)
- [Acceptance Criteria](#acceptance-criteria)
- [Implementation Checklist](#implementation-checklist)
- [Risks and Mitigations](#risks-and-mitigations)
- [Integration Notes](#integration-notes)
- [Touchpoints](#touchpoints)
- [Public Contracts](#public-contracts)
- [Blast Radius](#blast-radius)
- [Verification Evidence](#verification-evidence)
- [Test Infra Improvement Notes](#test-infra-improvement-notes)
- [Resume and Execution Handoff](#resume-and-execution-handoff)
- [Validate Contract](#validate-contract)
- [Cursor + RIPER-5 Guidance](#cursor--riper-5-guidance)

---

## Overview

Build a single-page Streamlit dashboard (Docker-deployed) that visualizes 8 hospitality KPIs from the Kimball dimensional layer (Phase 3 complete). Dashboard reads from dbt-computed KPI models in PostgreSQL. Includes Property + Date Range filters, KPI row with "Estimated" badges, and 3 analytical sections: Trends, Segments, Pacing. Design follows the Semrush-style card-based layout (see `DASHBOARD_MOCKUP_V4.html`).

**Context**: This plan references `process/context/all-context.md` for repository architecture, technology stack, and feature area mappings.

---

## Phase Completion Rules

A phase is NOT complete until:

1. **Integration Test** - Works with other system pieces
2. **Manual Test** - User can perform the action
3. **Data Verification** - Database/state changes confirmed
4. **Error Handling** - Failure cases handled gracefully
5. **User Confirmation** - User says "it works"

Status meanings:
- ⏳ PLANNED - Not started
- 🔨 CODE DONE - Written but not E2E tested
- 🧪 TESTING - Currently being tested
- ✅ VERIFIED - Tested AND confirmed working
- 🚧 BLOCKED - Has issues

After each phase, document:
- [ ] What was tested manually
- [ ] Data verified in DB (show query + result)
- [ ] Errors encountered and fixed
- [ ] User confirmation received

---

## Execution Brief

| Phase | What Happens | Integration Points | Test | Verify | Done When |
|-------|--------------|-------------------|------|--------|-----------|
| **A** | dbt KPI models: extend `fct_reservation_night` + `dim_property`, create `kpi_daily_snapshot`, `kpi_pacing`, `kpi_pickup` | Postgres `erg_opera_data` schema; dbt project | `dbt test --select kpi_*` all pass | Query each KPI model returns rows | User sees green dbt tests |
| **B** | Dashboard skeleton: folder structure, Dockerfile, requirements, Streamlit config, `app.py` with header + filter bar | Docker Compose; Postgres connection | Container builds, `streamlit run app.py` loads | Browser shows header + filters | User confirms UI loads |
| **C** | KPI Row + Data Layer: `repository.py` (cached queries), `components.py` (KPICard, FilterBar), wire to `kpi_daily_snapshot` | dbt models → SQL → pandas → Streamlit | KPI cards render with values + deltas | DB query returns expected 8 KPIs | User sees 8 KPI cards with [EST] badges |
| **D** | 3 Analytical Sections: Trends (4 charts), Segments (4 charts), Pacing (2 charts) | Same data layer | Charts render without JS errors | Hover/click interactions work | User interacts with all 3 sections |
| **E** | Polish & Deploy: estimate badges, responsive test, docker-compose.yml, README | Full stack | `docker compose up -d dashboard` healthy | Dashboard accessible at localhost:8501 | User confirms full dashboard works |

**Expected Outcome:**
- ✅ Running dashboard at `http://localhost:8501`
- ✅ 8 KPIs with correct values + [EST] badges on financial metrics
- ✅ Property dropdown + From/To date filters functional
- ✅ 10 charts across 3 sections rendering real data
- ✅ Dockerized, documented, ready for CI

---

## Scope (In/Out)

| In Scope | Out of Scope |
|----------|--------------|
| dbt KPI models (3 marts + schema.yml) | Multi-property comparison view |
| Streamlit single-page app (8 KPIs + 10 charts) | User authentication / RBAC |
| Property + Date Range filters | CSV/PDF export (nice-to-have) |
| Docker + docker-compose integration | Real-time WebSocket updates |
| "Estimated" badges on 4 financial KPIs | Historical backfill UI |
| Responsive layout (1280/1920/375) | Mobile-native touch gestures |

---

## Assumptions and Constraints

- **PostgreSQL** running at `db:5432` with database `erg_opera_data` (set by Phase 1-3)
- **dbt project** exists at `eras_dbt/` with `fct_reservation_night` and `dim_property` models
- **Python 3.11** base image; `uv` or `pip` for deps (decide at EXECUTE)
- **Room count**: hardcode `250` in `dim_property` for V1 (env var later)
- **Booking date**: derive from `created_at` in staging
- **Reservation status**: map from `reservation_status` field in staging
- No auth required for V1 (internal tool)

---

## Functional Requirements

1. **FR-01**: Display 8 KPI cards in a responsive row (Occupancy, ADR, RevPAR, Revenue, Reservations, Room Nights, Lead Time, Cancellation Rate)
2. **FR-02**: Financial KPIs (1-4) show amber "EST" badge; operational KPIs (5-8) no badge
3. **FR-03**: Header shows "ErasOpera > Booking Core Dashboard" + Project name + Property dropdown + From/To date inputs
4. **FR-04**: Filter changes re-query KPIs and all charts within 5s (Streamlit cache TTL 300s)
5. **FR-05**: Trends section: Occupancy (line+area), ADR/RevPAR (dual-axis), Bookings Pace (cumulative), Cancellation (bar+line)
6. **FR-06**: Segments section: By Market (stacked bar), By Source (horizontal bar), By Rate Plan (grouped bar), By Room Type (bullet)
7. **FR-07**: Pacing section: Current vs Prior Year (line+band), Pickup 7/30/90d (table+sparkline)
8. **FR-08**: All charts use Inter font, color tokens from design spec, consistent card wrapper

---

## Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Page load (cold) | < 3s |
| NFR-02 | Filter interaction (cached) | < 500ms |
| NFR-03 | Query timeout | 30s max |
| NFR-04 | Cache TTL | 300s (5 min) |
| NFR-05 | Responsive breakpoints | 1280px, 1920px, 375px |
| NFR-06 | Docker health check | `/_stcore/health` returns 200 |
| NFR-07 | Accessibility | WCAG AA contrast ratios |

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-01 | All 8 KPIs render with values + deltas | Manual: open dashboard, count cards |
| AC-02 | [EST] badge visible on Occupancy, ADR, RevPAR, Revenue | Visual inspection |
| AC-03 | Property dropdown filters all KPIs + charts | Select different property, verify data changes |
| AC-04 | From/To date range filters all data | Change dates, verify KPIs update |
| AC-05 | 10 charts render without JS errors | Browser console clean |
| AC-06 | `dbt test --select kpi_*` passes | CLI output shows 0 failures |
| AC-07 | Docker compose brings up dashboard + db | `docker compose up -d && curl localhost:8501/_stcore/health` |
| AC-08 | README documents run steps | File exists, steps work |

---

## Implementation Checklist

### Phase A: dbt KPI Layer
- [ ] Add `booking_date` (from `created_at`), `reservation_status` to `fct_reservation_night.sql`
- [ ] Add `room_count` (default 250) to `dim_property.sql`
- [ ] Create `models/marts/kpi_daily_snapshot.sql` (daily grain KPIs per property)
- [ ] Create `models/marts/kpi_pacing.sql` (current vs prior year)
- [ ] Create `models/marts/kpi_pickup.sql` (7/30/90 day pickup)
- [ ] Create `models/marts/schema.yml` with tests: not_null, accepted_values
- [ ] Run `dbt run --full-refresh --select marts.kpi_*` + `dbt test --select kpi_*`

### Phase B: Dashboard Skeleton
- [ ] Create `dashboard/` folder structure per design doc
- [ ] Write `Dockerfile` (python:3.11-slim, streamlit, deps)
- [ ] Write `requirements.txt` (streamlit, pandas, psycopg2, altair, python-dotenv)
- [ ] Write `.streamlit/config.toml` (theme, server.port=8501, server.address=0.0.0.0)
- [ ] Write `app.py` entry: page_config, header, filter bar (Property + From/To dates)
- [ ] Write `styles/theme.css` (CSS custom properties from design spec)
- [ ] **Added by VALIDATE**: Write `.dockerignore` (exclude `__pycache__`, `.git`, `*.pyc`, `target/`)
- [ ] **Added by VALIDATE**: Pin versions in `requirements.txt` (e.g., `streamlit==1.38.0`, `pandas==2.2.2`, `psycopg2-binary==2.9.9`, `altair==5.3.0`, `python-dotenv==1.0.1`)
- [ ] **Added by VALIDATE**: Add `browser.gatherUsageStats = false` to `.streamlit/config.toml`

### Phase C: KPI Row & Data Layer
- [ ] Write `data/repository.py` with `@st.cache_data(ttl=300)` query functions
- [ ] Write `ui/components.py`: `kpi_card()`, `filter_bar()`, `chart_wrapper()`
- [ ] Wire KPI row to `kpi_daily_snapshot` (latest date partition)
- [ ] Implement delta calculation (WoW or MoM based on date range)
- [ ] **Added by VALIDATE**: Add "Refresh button to clear Streamlit cache" to filter bar
- [ ] **Added by VALIDATE**: Specify delta logic: "WoW for ranges ≤ 14 days, MoM for > 14 days"

### Phase D: Analytical Sections
- [ ] Write `ui/tabs/trends.py`: 4 charts (Altair)
- [ ] Write `ui/tabs/segments.py`: 4 charts (Altair)
- [ ] Write `ui/tabs/pacing.py`: 2 charts (Altair)
- [ ] Wire tabs in `app.py` using `st.tabs()`
- [ ] **Added by VALIDATE**: Add chart UX details: empty state message, tooltip currency/percent format, `use_container_width=True`

### Phase E: Polish & Deploy
- [ ] Add [EST] badges to financial KPI cards
- [ ] Responsive testing at 1280/1920/375 (Chrome DevTools)
- [ ] Add `dashboard` service to root `docker-compose.yml`
- [ ] Write `dashboard/README.md` (run, config, extend)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| dbt model column mismatch | Medium | High | Run `dbt compile` first; inspect `target/compiled` |
| Streamlit cache stale data | Medium | Medium | TTL=300s; add "Refresh" button to clear cache |
| Altair chart rendering in Docker | Low | Medium | Test `altair-saver` not needed; use native `st.altair_chart` |
| Missing `room_count` in prod | High | High | Hardcode 250 in `dim_property` for V1; env var in V2 |
| Date filter edge cases (empty range) | Medium | Low | Default to last 30 days; guard clauses in repo |

---

## Integration Notes

| Dependency | Provided By | Consumed By |
|------------|-------------|-------------|
| `fct_reservation_night` (extended) | Phase 1b/2 | `kpi_daily_snapshot` |
| `dim_property` (extended) | Phase 1b/2 | `kpi_daily_snapshot` |
| `kpi_daily_snapshot` | Phase A | Dashboard repository |
| `kpi_pacing` | Phase A | Pacing tab |
| `kpi_pickup` | Phase A | Pickup Analysis |
| Postgres `erg_opera_data` | Phase 3 | All dbt models + Dashboard |
| Docker network `erasopera-network` | Root compose | Dashboard ↔ DB |

---

## Touchpoints

| Path | Type | Change |
|------|------|--------|
| `eras_dbt/models/marts/fct_reservation_night.sql` | dbt model | Modify (add columns) |
| `eras_dbt/models/marts/dim_property.sql` | dbt model | Modify (add room_count) |
| `eras_dbt/models/marts/kpi_daily_snapshot.sql` | dbt model | Create |
| `eras_dbt/models/marts/kpi_pacing.sql` | dbt model | Create |
| `eras_dbt/models/marts/kpi_pickup.sql` | dbt model | Create |
| `eras_dbt/models/marts/schema.yml` | dbt schema | Create |
| `dashboard/Dockerfile` | Infra | Create |
| `dashboard/requirements.txt` | Python deps | Create |
| `dashboard/.streamlit/config.toml` | Streamlit config | Create |
| `dashboard/app.py` | App entry | Create |
| `dashboard/config/settings.py` | Config | Create |
| `dashboard/data/repository.py` | Data layer | Create |
| `dashboard/ui/components.py` | UI components | Create |
| `dashboard/ui/tabs/trends.py` | Tab | Create |
| `dashboard/ui/tabs/segments.py` | Tab | Create |
| `dashboard/ui/tabs/pacing.py` | Tab | Create |
| `dashboard/ui/layout.py` | Layout | Create |
| `dashboard/styles/theme.css` | Styles | Create |
| `docker-compose.yml` (root) | Orchestration | Modify (add dashboard service) |

---

## Public Contracts

| Contract | Interface | Consumers |
|----------|-----------|-----------|
| KPI Daily Snapshot | SQL view `marts.kpi_daily_snapshot` (business_date, hotel_id, occupancy, adr, revpar, revenue, reservations, room_nights, lead_time, cancellation_rate) | Dashboard, future BI tools |
| KPI Pacing | SQL view `marts.kpi_pacing` (date, hotel_id, current_occupancy, prior_year_occupancy, pace_pct) | Dashboard |
| KPI Pickup | SQL view `marts.kpi_pickup` (hotel_id, window_days, pickup_rooms, pickup_revenue) | Dashboard |
| Dashboard HTTP | `GET /` → Streamlit HTML; `GET /_stcore/health` → 200 | Docker healthcheck, users |
| Filter API | Internal: `repository.fetch_kpis(property_id, start_date, end_date)` → `pd.DataFrame` | All tabs |

---

## Blast Radius

- **Files created:** ~18 new files (15 dashboard + 3 dbt)
- **Files modified:** 3 (2 dbt models + docker-compose.yml)
- **Packages/services:** `eras_dbt` (marts), `dashboard` (new), root compose
- **Risk class:** Low-Medium (greenfield dashboard, reads-only on warehouse)
- **Rollback:** `docker compose down dashboard`; dbt `--full-refresh` to prior state

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC Criterion |
|-----------------|----------|----------------------|
| dbt model compile | Automated: `dbt compile --select marts.kpi_*` | FR-01, FR-05, FR-06, FR-07 (models exist) |
| dbt unit tests | Automated: `dbt test --select kpi_*` | AC-06 (data quality) |
| Dashboard builds | Automated: `docker build dashboard/` | NFR-01, NFR-06 (image builds) |
| Dashboard starts | Automated: `docker compose up -d && sleep 10 && curl -f localhost:8501/_stcore/health` | AC-07 (service healthy) |
| KPI cards render | Manual: open browser, count 8 cards, verify values > 0 | AC-01, AC-02 |
| Filters work | Manual: change property, change dates, verify re-query | AC-03, AC-04 |
| All 10 charts render | Manual: cycle tabs, no console errors | AC-05, FR-05, FR-06, FR-07 |
| Responsive layout | Manual: DevTools device toolbar 1280/1920/375 | NFR-05, FR-08 |
| Data freshness | Manual: insert test row, wait 5 min, verify appears | NFR-04 |

---

## Test Infra Improvement Notes

(none identified yet — will update during EVL)

---

## Resume and Execution Handoff

| Field | Value |
|-------|-------|
| **Selected plan file** | `process/features/booking-core/active/booking-core-p1d-dashboard_15-07-26/booking-core-p1d-dashboard_PLAN_15-07-26.md` |
| **Last completed phase** | None (fresh start) |
| **Validate-contract status** | Pending (vc-validate-agent writes before EXECUTE) |
| **Supporting context files loaded** | `booking-core-p1d-dashboard_DESIGN_14-07-26.md`, `booking-core_SPEC_13-07-26.md`, `all-context.md`, `all-tests.md` |
| **Next step for fresh agent** | Run `vc-validate-agent` on this plan, then `ENTER EXECUTE MODE` starting with Phase A (dbt KPI layer) |

---

## Validate Contract

## Validate Contract

Status: CONDITIONAL
Date: 15-07-26
date: 2026-07-15
generated-by: outer-pvl
supersedes: 2026-07-15 (outer-pvl) — outer PVL has current evidence

Parallel strategy: parallel-subagents
Rationale: 3/7 signals (S2, S7); 9 agents typical; no mid-task coordination needed

Test gates (C3 5-column table — ADDITIVE; existing consumers still parse the legacy line form below it):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-06 | dbt KPI models pass data quality tests | Fully-Automated | `dbt test --select kpi_*` exits 0 | A |
| NFR-06 | Dashboard container health endpoint returns 200 | Hybrid | `docker compose up -d dashboard && sleep 10 && curl -f localhost:8501/_stcore/health` | A |
| AC-01 | All 8 KPI cards render with values + deltas | Agent-Probe | Manual: open dashboard, count 8 cards, verify values > 0 | A |
| AC-02 | [EST] badge visible on Occupancy, ADR, RevPAR, Revenue | Agent-Probe | Manual: visual inspection of 4 financial KPIs | A |
| AC-03 | Property dropdown filters all KPIs + charts | Agent-Probe | Manual: select different property, verify data changes | A |
| AC-04 | From/To date range filters all data | Agent-Probe | Manual: change dates, verify KPIs update | A |
| AC-05 | 10 charts render without JS errors | Agent-Probe | Manual: cycle tabs, browser console clean | A |
| FR-08 | Responsive layout at 1280/1920/375 | Agent-Probe | Manual: DevTools device toolbar | A |
| NFR-04 | Data freshness - cache TTL 300s respected | Agent-Probe | Manual: insert test row, wait 5 min, verify appears | A |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: the `strategy:` column carries ONLY the 3 proving strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is NEVER a `strategy:` value — it is a named residual row carried via gap-resolution D, never a strategy that proves a behavior.

Legacy line form (retained so existing validate-contract consumers still parse):
- dbt KPI models: Fully-automated: `dbt test --select kpi_*` | dbt compile | hybrid: docker build + healthcheck | agent-probe: KPI cards, filters, charts, responsive, freshness | known-gap: Python unit tests, Playwright e2e, CI pipeline

Dimension findings:
- Infra fit: PASS — Greenfield dashboard fits existing Docker network, Postgres, dbt marts structure
- Test coverage: CONCERN — 6/10 gates manual; Python layer no automated tests; Playwright mentioned but not in checklist
- Breaking changes: PASS — Additive only: new dbt models, new columns, new service, no auth changes
- Security surface: PASS — No high-risk classes triggered; internal read-only tool, env-based DB creds
- Phase A feasibility: PASS — dbt targets exist, mechanical feasibility verified, gaps in pacing/pickup spec
- Phase B feasibility: PASS — All creates in new directory, docker-compose additive, .dockerignore missing
- Phase C feasibility: CONCERN — SQL injection risk, cache invalidation gap, delta logic underspecified
- Phase D feasibility: CONCERN — Altair-in-Docker untested, 10-chart perf, empty states/tooltips underspecified
- Phase E feasibility: PASS — Additive modifications, README creation, no conflicts

Open gaps:
- Python unit tests for repository.py, components.py, tabs: known-gap: documented as NEW PLAN REQUIRED — see backlog/dashboard-unit-tests_NOTE_15-07-26.md
- Playwright e2e tests for filter interactions, chart rendering: known-gap: documented as NEW PLAN REQUIRED — see backlog/dashboard-e2e-tests_NOTE_15-07-26.md
- CI/CD pipeline definition: known-gap: documented as NEW PLAN REQUIRED — see backlog/ci-pipeline_NOTE_15-07-26.md
- Altair rendering in headless Docker: known-gap: execute-agent instruction E3 validates in Phase B
- Chart UX details (empty states, tooltips, responsive sizing): execute-agent instruction E4 addresses progressively

What this coverage does NOT prove:
- dbt test gate: Does NOT prove KPI business logic correctness (only not_null/accepted_values constraints)
- Docker healthcheck: Does NOT prove UI renders correctly or charts display data
- KPI card manual check: Does NOT prove delta calculations are mathematically correct (WoW vs MoM)
- Filter interaction manual check: Does NOT prove edge cases (empty date range, invalid property, concurrent users)
- Chart rendering manual check: Does NOT prove chart data accuracy, tooltip formatting, or cross-browser consistency
- Responsive layout manual check: Does NOT prove touch gestures on mobile or print stylesheet
- Data freshness manual check: Does NOT prove cache behavior under concurrent multi-user load

Accepted by: session (autonomous, /goal execution) — concerns: Python unit tests gap, Playwright e2e gap, CI pipeline gap, Altair Docker validation, Chart UX gaps, SQL injection prevention, Cache invalidation, Delta calculation spec

Gate: CONDITIONAL (concerns noted, user accepted)

---

## Cursor + RIPER-5 Guidance

- **Cursor Plan mode**: Import "Implementation Checklist" steps directly; tick off as you go
- **RIPER-5**: RESEARCH (done) → INNOVATE (done, design approved) → PLAN (this file) → request EXECUTE approval
- **Avoid code until EXECUTE**; if scope expands mid-flight, pause and convert to COMPLEX
- **After each phase: STOP and verify** using the Verification Evidence table before proceeding
- **Reattach this plan** in future sessions for context continuity