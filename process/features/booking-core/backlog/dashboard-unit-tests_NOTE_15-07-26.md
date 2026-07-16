# Backlog Note: Dashboard Python Unit Tests

**Date:** 2026-07-15  
**Feature:** booking-core  
**Phase:** 1d Dashboard  
**Source:** VALIDATE phase (PVL) - Test Coverage CONCERN, Phase C gap

---

## Gap Description

The Phase 1d Dashboard plan has no Python unit tests for the data layer (`repository.py`), UI components (`components.py`), or tab modules (`trends.py`, `segments.py`, `pacing.py`). The Validation Evidence table lists only dbt tests and manual checks.

## Impact

- No automated regression for SQL query logic, data transformations, delta calculations
- SQL injection vulnerabilities could go undetected
- Cache invalidation logic untested
- Delta calculation (WoW/MoM) logic untested

## Proposed Resolution

Create pytest test suite in `dashboard/tests/`:

### `dashboard/tests/conftest.py`
- Fixtures: mock DB connection, sample DataFrame responses, test date ranges
- `mock_db_conn` - psycopg2 connection mock
- `sample_kpi_data` - DataFrame matching `kpi_daily_snapshot` schema
- `sample_pacing_data` - DataFrame matching `kpi_pacing` schema
- `sample_pickup_data` - DataFrame matching `kpi_pickup` schema

### `dashboard/tests/test_repository.py`
- `test_fetch_kpi_daily_snapshot_returns_dataframe`
- `test_fetch_kpi_daily_snapshot_filters_by_date_range`
- `test_fetch_kpi_daily_snapshot_filters_by_property`
- `test_fetch_kpi_daily_snapshot_uses_parameterized_query` (SQL injection prevention)
- `test_fetch_kpi_daily_snapshot_cache_ttl` (verify @st.cache_data ttl=300)
- `test_fetch_pacing_data_compares_current_vs_prior_year`
- `test_fetch_pickup_data_windows_7_30_90`
- `test_repository_handles_db_connection_error_gracefully`
- `test_repository_handles_empty_result_set`

### `dashboard/tests/test_components.py`
- `test_kpi_card_renders_label_value_delta`
- `test_kpi_card_shows_est_badge_when_financial`
- `test_kpi_card_shows_no_badge_when_operational`
- `test_filter_bar_returns_selected_property_and_dates`
- `test_chart_wrapper_renders_altair_chart`

### `dashboard/tests/test_tabs.py`
- `test_trends_tab_occupancy_chart_data_shape`
- `test_trends_tab_adr_revpar_dual_axis`
- `test_segments_tab_market_stacked_bar`
- `test_pacing_tab_pickup_table_structure`

### `dashboard/tests/test_delta_calculation.py` (NEW - from VALIDATE gap)
- `test_delta_wow_when_range_le_14_days`
- `test_delta_mom_when_range_gt_14_days`
- `test_delta_handles_zero_prior_period`
- `test_delta_handles_null_values`

## Estimated Effort

- conftest.py fixtures: 30 min
- repository tests: 1.5-2 hours
- components tests: 1 hour
- tabs tests: 1.5 hours
- delta calculation tests: 1 hour (new from VALIDATE)
- **Total: ~5-6 hours**

## Acceptance Criteria

- [ ] `pytest dashboard/tests/` runs and passes
- [ ] Coverage > 80% for `repository.py`, `components.py`
- [ ] SQL injection test verifies parameterized queries (no f-strings in SQL)
- [ ] Cache TTL test verifies 300s decorator
- [ ] Delta calculation tests verify WoW/MoM logic
- [ ] Tests run in CI without database (mocked)
- [ ] Fixtures use realistic data from dbt model schemas

## Dependencies

- `pytest`, `pytest-mock`, `pandas` in dev dependencies
- Can be implemented during/after Phase C
- Required for CI pipeline (ci-pipeline_NOTE)

## Related

- `dashboard-e2e-tests_NOTE_15-07-26.md` (Playwright e2e)
- `ci-pipeline_NOTE_15-07-26.md` (CI integration)
- VALIDATE execute-agent instruction E1
- VALIDATE execute-agent instruction E2