# Backlog Note: Dashboard E2E Tests (Playwright)

**Date:** 2026-07-15  
**Feature:** booking-core  
**Phase:** 1d Dashboard  
**Source:** VALIDATE phase (PVL) - Test Coverage CONCERN

---

## Gap Description

The Phase 1d Dashboard plan has no automated end-to-end tests for browser interactions. The Design doc test table mentions Playwright for filter interactions and visual checks, but the Implementation Checklist doesn't include it. Currently 6/10 verification gates are manual.

## Impact

- No automated regression for filter interactions, chart rendering, responsive behavior
- Manual testing doesn't catch visual regressions or JS errors in CI
- No confidence in cross-browser compatibility

## Proposed Resolution

Create Playwright e2e test suite:

1. **`tests/e2e/dashboard.spec.ts`** - Core dashboard flow
   - Page loads at localhost:8501
   - Health endpoint returns 200
   - 8 KPI cards render with values > 0
   - [EST] badges visible on 4 financial KPIs

2. **`tests/e2e/filters.spec.ts`** - Filter interactions
   - Property dropdown changes KPI values
   - Date range picker updates all charts
   - Empty date range shows guard state
   - Rapid filter changes don't cause race conditions

3. **`tests/e2e/charts.spec.ts`** - Chart rendering
   - All 10 charts render without JS console errors
   - Hover tooltips show formatted values
   - Responsive at 1280px, 1920px, 375px viewports
   - Empty date range shows appropriate empty state

4. **`tests/e2e/visual.spec.ts`** - Visual regression (optional V2)
   - Screenshot comparison for KPI row
   - Screenshot comparison for each tab

## Estimated Effort

- Setup Playwright + TypeScript config: 30 min
- Core dashboard tests: 1-2 hours
- Filter tests: 1-2 hours
- Chart tests: 2-3 hours
- Visual regression setup: 1 hour (defer to V2)
- **Total: ~5-8 hours**

## Acceptance Criteria

- [ ] `npx playwright test` runs and passes in CI
- [ ] Tests run against `docker compose up -d` dashboard
- [ ] No flaky tests (retry config for Streamlit hydration)
- [ ] Viewport tests cover 3 breakpoints
- [ ] Console error detection fails test on any JS error

## Dependencies

- Requires dashboard running (docker compose)
- Playwright, @playwright/test in dev dependencies
- Can be done after Phase E (dashboard deployed)
- CI pipeline needed to run in automation (see ci-pipeline_NOTE)

## Related

- `dashboard-unit-tests_NOTE_15-07-26.md` (Python unit tests)
- `ci-pipeline_NOTE_15-07-26.md` (CI integration)