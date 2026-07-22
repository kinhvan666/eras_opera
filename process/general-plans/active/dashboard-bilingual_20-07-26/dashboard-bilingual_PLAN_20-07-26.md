---
name: plan:dashboard-bilingual
description: Add EN/VI bilingual support to the Streamlit dashboard via a dict-based i18n module + header language switch
date: 20-07-26
feature: (general) dashboard
phase: "standalone"
---

# Dashboard Bilingual (EN/VI) Plan

Complexity: SIMPLE
Status: PLANNED
Date: 2026-07-20
Scope: Add a language toggle (EN | VI) to the dashboard header and translate ALL user-facing UI copy across the main dashboard (header, filters, KPI tiles, all 4 tabs). Db-sourced codes stay untranslated.

---

## Overview

The ErasOpera Streamlit dashboard currently hardcodes all English UI strings. This plan adds bilingual
support (English + Vietnamese) with a header language switch (two buttons `EN | VI` next to the refresh
button). Translation is driven by a new dict-based i18n module `dashboard/ui/i18n.py` exposing `t(key)`
and a `st.session_state["lang"]` toggle.

Decisions locked in INNOVATE:
- **Switch UI:** two buttons `EN | VI` in the header row, next to the existing refresh button.
- **OPERA business codes stay English:** `revenue_category` (Room/FnB/ServiceCharge/Other), `market_code`,
  `rate_plan_code`, `room_type`, `source_of_business` are DB codes — NOT translated. Only the legend
  *title* "Category" is translated. `period`/`Metric`/`Status` display labels in pacing.py ARE translated.

RESEARCH inventory (vc-research-agent, 2026-07-20) identified ~110 hardcoded strings across:
`app.py`, `ui/components.py`, `ui/tabs/revenue.py`, `ui/tabs/trends.py`, `ui/tabs/segments.py`,
`ui/tabs/pacing.py`. DB-origin values that must NOT be run through `t()`: market_code, rate_plan_code,
room_type, source_of_business, revenue_category (+ "Tax" filter literal).

---

## Touchpoints

- `dashboard/ui/i18n.py` — **NEW** translation dict + `t()` helper (the "i18n module")
- `dashboard/app.py` — import i18n; add EN/VI toggle buttons in header; wrap all hardcoded strings in `t()`
- `dashboard/ui/components.py` — no logic change required (label/title injected from callers); verify kpi_card / chart_wrapper accept translated args
- `dashboard/ui/tabs/revenue.py` — wrap axis/tooltip/chart titles, radio options, info messages, category legend title in `t()`
- `dashboard/ui/tabs/trends.py` — same as revenue.py for trends charts
- `dashboard/ui/tabs/segments.py` — wrap chart titles, axis titles; convert raw-column tooltips to explicit `alt.Tooltip(..., title=t(...))`
- `dashboard/ui/tabs/pacing.py` — wrap titles/messages; translate `period` map, `Metric`/`Status` display values; KEEP stable internal sort keys for Metric/Status so Altair domain stays in sync

---

## Public Contracts

- New module `dashboard/ui/i18n.py` with `T` dict and `t(key, **kwargs)` function.
- `t()` signature: `t(key: str, **kwargs) -> str`; reads `st.session_state.get("lang", "en")`.
- No changes to data layer (`data/repository.py`) or DB schema.

## Blast Radius

- **Files modified:** 6 (app.py + 4 tabs + components.py verification)
- **Files created:** 1 (ui/i18n.py)
- **Data touched:** none (no DB, no schema)
- **Risk class:** LOW — pure UI text swap; rerun-based language switch
- **Rollback:** remove toggle + revert strings (git revert) — no data impact

---

## Implementation Checklist

### Step 1 — Create i18n module
Create `dashboard/ui/i18n.py` with a `T` dict (en/vi) and `t(key, **kwargs)` helper that reads
`st.session_state.get("lang", "en")`. Include all keys listed in the RESEARCH inventory:
app title, header refresh/data-as-of, lang labels, filters (Property/All Properties/From/To/30D/90D/MTD/YTD),
error/info messages, 9 KPI labels, 4 tab titles, revenue/trends/segments/pacing chart titles, axis/tooltip
titles, radio options (By Month/By Day), and pacing display labels (period/Metric/Status). Vietnamese
values provided for every key (all UI copy translated; OPERA codes Room/FnB/ServiceCharge/Other and
market/rate/room/source codes stay as raw English values, not keys).

### Step 2 — Header toggle in app.py
- Init `st.session_state["lang"]` default `"en"` at top if missing.
- Add two small buttons `EN | VI` next to the refresh link (callback sets `st.session_state["lang"]`).
- Wrap branding span, refresh `title=` attribute, and `"Data as of {as_of_str}"` in `t()`.
- `st.set_page_config(page_title=t("app.title"))`.

### Step 3 — Filters + KPI + tabs in app.py
Wrap: Property/All Properties/From/To/30D/90D/MTD/YTD, load errors, no-reservation message, all 9 KPI
labels, and the 4 tab titles in `t()`.

### Step 4 — revenue.py
Wrap radio default + options (By Month/By Day), chart titles (Revenue by Month/Day, by Market Segment,
by Rate Plan, by Room Type), axis/tooltip titles (Month/Date/Revenue (₫)/Category/Revenue ₫/Segment/Rate
Plan/Room Type), info messages. `CATEGORY_ORDER` (raw DB) unchanged; only legend title "Category" → `t("axis.category")`.

### Step 5 — trends.py
Wrap radio options, chart titles (Revenue/Occupancy/ADR/Cancellation Rate by Month/Day), axis/tooltip
titles (Month/Date/Revenue (₫)/Revenue ₫/Occupancy/ADR (₫)/ADR ₫/Cancellation Rate/Canc. Rate), and
"No data for selected range."

### Step 6 — segments.py
Wrap chart titles (Room Nights by Market/Source/Rate Plan/Room Type), axis titles (Market/Source/Room
Nights/Rate Plan/Room Type), info messages. Convert raw-column tooltips (`tooltip=["market_code","room_nights"]`
etc.) to explicit `alt.Tooltip("room_nights:Q", title=t("axis.room_nights"))`; keep code columns raw.

### Step 7 — pacing.py (highest risk)
- Translate `period` map, `Metric` display column, `Status` lambda via shared constants.
- KEEP stable internal sort keys for Altair `sort`/`scale` domain (occupancy/adr/revpar/revenue, ahead/behind),
  translate only display labels — never hardcode translated strings in `sort=[...]`.
- Translate all chart titles, axis/tooltip titles, captions, info messages, and the pickup table rename
  map ("Window (days)"/"Rooms"/"Revenue (₫)") — update `column_config` + Altair tooltip refs in lockstep.
- DB codes stay raw.

### Step 8 — Verify
- Run `streamlit run app.py --server.port=8510`; snapshot with agent-browser.
- Toggle EN → VI, confirm all visible strings switch and charts still render (no Altair domain errors).
- Sanity grep for leftover English UI literals that should have been wrapped (excluding DB-code lists and ₫ strings).

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves |
|---|---|---|
| Dashboard runs, no import/syntax error | Hybrid (local streamlit) | i18n module + t() wiring valid |
| EN default renders all English strings | Agent-probe (agent-browser snapshot) | baseline copy correct |
| VI toggle swaps all UI copy | Agent-probe (snapshot after click VI) | t() + session_state toggle works |
| Charts render in both langs (no Altair domain error) | Agent-probe | pacing Metric/Status sort-domain sync correct |
| DB codes (Room/FnB/rate_plan_code/...) stay English | Agent-probe | revenue_category not translated per decision |

## Test Infra Improvement Notes
(none — UI text swap, verified via browser snapshot)

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| pacing.py Metric/Status sort-domain breaks under VI | MED | use stable internal keys for sort/scale domain, translate only display labels |
| segments.py raw-column tooltips not localized | LOW | convert to explicit alt.Tooltip with t() title |
| Leftover English literal after refactor | LOW | grep sanity scan in Step 8 |
| `t()` called before session_state init | LOW | init `lang` default at top of app.py |

## Resume and Execution Handoff
1. Selected plan: `process/general-plans/active/dashboard-bilingual_20-07-26/dashboard-bilingual_PLAN_20-07-26.md`
2. Last completed phase: PLAN (awaiting VALIDATE → EXECUTE)
3. Prereq: dashboard runs against Postgres (already proven); agent-browser available for snapshot verify.
4. Context: RESEARCH inventory from vc-research-agent; INNOVATE decisions (Option A toggle, keep OPERA codes EN).

---

## Acceptance Criteria

1. Dashboard starts with no import/syntax error; `dashboard/ui/i18n.py` imports cleanly.
2. Default language is EN; all visible UI copy renders in English (matches current behavior).
3. Clicking `VI` button switches every user-facing string to Vietnamese (header, filters, KPI tiles, all 4 tabs, chart titles, axes, tooltips, messages).
4. Clicking `EN` switches back to English; choice persists across filter/tab interactions (session_state).
5. All charts render in both languages with no Altair domain/sort errors (pacing Metric/Status sync correct).
6. OPERA business codes (Room/FnB/ServiceCharge/Other, market_code, rate_plan_code, room_type, source_of_business) stay English in both languages.
7. No data layer or DB schema changed.

## Phase Completion Rules

This plan is SIMPLE (single execution session). A phase/step is COMPLETE only when:
1. Code runs without import/syntax error (streamlit starts).
2. Agent-browser snapshot confirms EN and VI both render all expected strings.
3. Charts render without Altair errors in both languages.
4. Grep sanity scan shows no leftover English UI literals that should be wrapped.

Status markers used:
- ⏳ PLANNED — not started
- 🔨 CODE DONE — command run, output not yet verified
- ✅ VERIFIED — verified with browser snapshot or command output
- 🚧 BLOCKED — issue preventing completion

## Validate Contract

Status: PASS
Date: 20-07-26
date: 2026-07-20
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 1 dominant signal — single execution session, pure UI text swap with no cross-agent coordination; code must be written then verified in-order (i18n module first, then app.py, then tabs).

Test gates (C3 5-column table — ADDITIVE):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| TC1 | Dashboard imports & runs (i18n module + t() wiring valid) | Hybrid | `streamlit run app.py --server.port=8510` starts without ImportError; agent-browser open http://localhost:8510 returns HTTP 200 | A |
| TC2 | EN default renders all English copy | Agent-Probe | agent-browser snapshot -i on default load; confirm English strings (Property, Revenue, Occupancy, tabs Revenue/Trends/Segments/Pacing) present | A |
| TC3 | VI toggle swaps all UI copy | Agent-Probe | click VI button, snapshot; confirm Vietnamese strings (Thuộc tính, Doanh thu, Tỷ lệ lấp đầy, tabs Doanh thu/Xu hướng/Phân khúc/Pace) present and no English UI copy remains | A |
| TC4 | Charts render in both langs, no Altair domain error | Agent-Probe | snapshot each tab under EN and VI; confirm charts present, no Streamlit/Altair exception text; pacing Metric/Status sort sync correct | A |
| TC5 | OPERA codes stay English in both langs | Agent-Probe | snapshot revenue/pacing tabs; confirm Room/FnB/ServiceCharge/Other and rate_plan_code/market_code values unchanged under VI | A |

Legacy line form:
- Infra fit: Hybrid: streamlit starts + HTTP 200 | snapshot EN/VI
- Test coverage: Agent-Probe: browser snapshot proves copy swap + chart render
- Breaking changes: none — 0 schema/API/auth changes; pure UI string swap
- Security surface: none — no new auth, endpoint, or credential surface

Dimension findings:
- Infra fit: PASS — dashboard + Postgres already proven running; agent-browser installed and used successfully this session
- Test coverage: PASS — 5 gates cover import/run, EN baseline, VI swap, chart render, code-preservation; verified via browser snapshot
- Breaking changes: PASS — no schema/API/auth/public-surface change; i18n module is additive
- Security surface: PASS — no new credentials, endpoints, or trust-boundary changes

Open gaps:
- none (execution-layer gaps would surface at EVL; this is a text-swap with full snapshot coverage)

What this coverage does NOT prove:
- TC2/TC3 do not prove every single one of ~110 strings is individually correct Vietnamese — they prove the toggle mechanism works and representative strings swap; full linguistic review is manual
- TC4 does not prove visual layout/overflow correctness of longer Vietnamese labels (e.g. "Tỷ lệ lấp đầy" vs "Occupancy" width) — layout may need a visual pass
- TC5 does not prove DB codes render identically in both langs at the data level (they are untouched by design, verified by code review not runtime diff)

Gate: PASS (no FAILs, plan structure valid, all touchpoints resolve)
Accepted by: session (autonomous validate for operational UI feature)

## Autonomous Goal Block

Goal: Make the ErasOpera Streamlit dashboard bilingual (EN/VI) with a header EN|VI toggle, translating all user-facing UI copy while keeping OPERA business codes in English.
Scope: Create dashboard/ui/i18n.py; add header toggle; wrap ~110 strings across app.py + 4 tabs.
Evidence gate: dashboard runs; EN and VI both render via browser snapshot; charts render without Altair errors; OPERA codes unchanged.
Out-of-scope: executive/ dashboard (separate pass), DB-code translation, query-param language persistence.
