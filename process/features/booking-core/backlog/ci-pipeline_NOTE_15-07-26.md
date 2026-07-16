# Backlog Note: CI/CD Pipeline for Dashboard

**Date:** 2026-07-15  
**Feature:** booking-core  
**Phase:** 1d Dashboard  
**Source:** VALIDATE phase (PVL) - Test Coverage CONCERN, Phase E gap

---

## Gap Description

The Phase 1d Dashboard plan has no CI/CD pipeline definition. The Implementation Checklist ends at "Write README.md" with no automation for:
- dbt model compilation and testing
- Docker image building
- Python unit tests (when added)
- Playwright e2e tests (when added)
- Deployment validation

## Impact

- No automated gate before merge
- Manual verification required for every change
- No enforcement of test gates from validate-contract
- Cannot integrate with future feature branches

## Proposed Resolution

Create GitHub Actions workflow:

### `.github/workflows/dashboard-ci.yml`

**Jobs:**
1. **dbt-check** - Runs on `eras_dbt/` changes
   - `dbt deps`
   - `dbt compile --select marts.kpi_*`
   - `dbt test --select kpi_*`
   - Uses PostgreSQL service container

2. **dashboard-unit-tests** - Runs on `dashboard/` Python changes
   - Install deps (uv/pip)
   - `pytest dashboard/` with coverage
   - Requires: dashboard-unit-tests backlog implemented

3. **dashboard-build** - Runs on `dashboard/` changes
   - `docker build dashboard/ -t erasopera/dashboard:test`
   - Scan for vulnerabilities (Trivy/Snyk optional)

4. **dashboard-e2e** - Runs on `dashboard/` changes (after build)
   - `docker compose up -d dashboard postgres`
   - Wait for healthcheck
   - `npx playwright test`
   - Requires: dashboard-e2e-tests backlog implemented

5. **integration-smoke** - Runs on any change to plan area
   - Full stack up: `docker compose up -d`
   - Verify all services healthy
   - Basic connectivity test

### `.github/workflows/dashboard-cd.yml` (Optional V2)
- Deploy to staging on main branch
- Blue/green or rolling update
- Health verification post-deploy

## Estimated Effort

- GitHub Actions workflow files: 2-3 hours
- Service container config (Postgres for dbt): 1 hour
- Docker layer caching optimization: 30 min
- **Total: ~4-5 hours** (without test implementations)

## Acceptance Criteria

- [ ] `dbt test --select kpi_*` runs in CI and blocks merge on failure
- [ ] `pytest dashboard/` runs in CI (when unit tests exist)
- [ ] `docker build dashboard/` runs in CI
- [ ] `npx playwright test` runs in CI (when e2e tests exist)
- [ ] Workflow runs on PR to main, blocks merge on failure
- [ ] Artifacts uploaded (dbt target/, pytest coverage, playwright screenshots)

## Dependencies

- `dashboard-unit-tests_NOTE_15-07-26.md` - Python unit tests
- `dashboard-e2e-tests_NOTE_15-07-26.md` - Playwright e2e tests
- GitHub repository with Actions enabled
- PostgreSQL service container for dbt tests

## Related

- `dashboard-unit-tests_NOTE_15-07-26.md`
- `dashboard-e2e-tests_NOTE_15-07-26.md`
- Phase E checklist item: "Add to docker-compose.yml" (prereq for CI docker compose up)