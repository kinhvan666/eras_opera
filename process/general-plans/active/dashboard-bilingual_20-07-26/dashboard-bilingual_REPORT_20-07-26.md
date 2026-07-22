---
phase: dashboard-bilingual
date: 2026-07-20
status: COMPLETE
feature: (general) dashboard
plan: process/general-plans/active/dashboard-bilingual_20-07-26/dashboard-bilingual_PLAN_20-07-26.md
---

# Dashboard Bilingual (EN/VI) — Execute Report

## What Was Done

Implemented bilingual EN/VI support per `dashboard-bilingual_PLAN_20-07-26.md`:

1. **Created `dashboard/ui/i18n.py`** — dict `T={en,vi}` with ~90 keys covering all UI copy + `t(key, **kwargs)` helper reading `st.session_state["lang"]`.
2. **`app.py`** — init `lang` default "en"; header row with real `st.button` EN/VI toggle (next to refresh); wrapped branding/title/refresh-title/data-as-of, filters (Property/All Properties/From/To/30D/90D/MTD/YTD), load errors, 9 KPI labels, 4 tab titles.
3. **`ui/tabs/revenue.py`** — wrapped View radio, chart titles, axis/tooltip titles; `CATEGORY_ORDER` (raw DB) untouched; only legend title translated.
4. **`ui/tabs/trends.py`** — wrapped radio, all 4 chart titles, axis/tooltip titles.
5. **`ui/tabs/segments.py`** — wrapped chart titles, axis titles; converted raw-column tooltips to explicit `alt.Tooltip(..., title=t(...))`; DB codes (market_code etc.) stay raw.
6. **`ui/tabs/pacing.py`** — wrapped titles/messages; translated `period` map, `Metric`/`Status` via shared label maps; **kept stable internal keys** (`current_occupancy`/`prior_occupancy`, `metric_key`, `ahead`/`behind`) for Altair sort/scale domain so VI translation does not break charts; pickup rename map + column_config updated in lockstep.

## What Was Skipped or Deferred

- None. All checklist items implemented.

## Test Gate Outcomes

| Gate | Result |
|---|---|
| TC1 dashboard imports & runs | ✅ PASS — streamlit starts HTTP 200, no ImportError |
| TC2 EN default renders English | ✅ PASS — snapshot shows Property/Revenue/Occupancy/By Month/30D/Trends etc. |
| TC3 VI toggle swaps all UI copy | ✅ PASS — snapshot shows Thuộc tính/Doanh thu/Tỷ lệ lấp đầy/30N/Đầu tháng/Pace |
| TC4 charts render both langs, no Altair error | ✅ PASS — all 4 tabs render without exception; pacing sort-domain sync correct |
| TC5 OPERA codes stay English | ✅ PASS — CATEGORY_ORDER / market_code / rate_plan_code / room_type / source_of_business untouched by design |

Verified via agent-browser snapshots at http://localhost:8510 (EN default + after clicking VI).

## Plan Deviations

None. Implementation matches plan exactly. (Note: header toggle uses Streamlit `st.button` with `on_click` updating `session_state["lang"]` rather than HTML buttons — plan Step 2 described "two buttons" without mandating HTML; Streamlit buttons are the correct mechanism since pure-HTML buttons cannot fire Python callbacks. Within-blast-radius, no approval needed.)

## Test Infra Gaps Found

- No automated test for i18n (browser-snapshot verification only). Acceptable for a text-swap UI feature; if desired, a future test could assert `t("kpi.revenue", lang="vi") == "Doanh thu"`.

## Closeout Packet

- Selected plan: process/general-plans/active/dashboard-bilingual_20-07-26/dashboard-bilingual_PLAN_20-07-26.md
- Finished: bilingual EN/VI dashboard with header toggle
- Verified: EN + VI snapshots, charts render, OPERA codes preserved
- Unverified: per-string linguistic perfection (manual review only); long-Vietnamese-label layout overflow not visually measured
- Next: commit & push; optionally extend to executive/ dashboard (out of scope)

## Forward Preview

- **Test Infra Found:** agent-browser snapshot is the verification path for UI/i18n changes
- **Blast Radius Changes:** 6 files modified/created (app.py, 4 tabs, new ui/i18n.py); no schema/DB change
- **Commands to Stay Green:** `streamlit run app.py --server.port=8510`; agent-browser snapshot to verify toggle
- **Dependency Changes:** none
