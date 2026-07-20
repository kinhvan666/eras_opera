---
name: plan:financials-postings-phase-01-cashiering-extractor
description: "Cashiering postings pipeline — Phase 1: extractor + raw.cashiering_postings"
date: 17-07-26
metadata:
  node_type: memory
  type: plan
  feature: financials
  phase: phase-01
---

# Phase 01 — Extractor + Raw Table

**Program:** financials-postings
**Umbrella plan:** process/features/financials/active/financials_17-07-26/financials-postings-umbrella_PLAN_17-07-26.md
**Phase status:** COMPLETE
**Report destination:** process/features/financials/active/financials_17-07-26/phase-01-cashiering-extractor_REPORT_{dd-mm-yy}.md (flat in the program task folder)

---

## Purpose

Extract raw cashiering postings from OPERA Cloud `/financialPostings` (Cashiering API, see
`docs/OPERA Cloud Cashiering API (26.2.0.0).json`) into a new raw table `raw.cashiering_postings`,
upserted on `transaction_no`. This is the foundation layer — every downstream phase (staging,
fct_folio_line, additive fct_reservation_night columns, dashboard) depends on this raw data
existing and being correctly deduplicated. Follows the extraction/pagination/upsert patterns
already proven in `extractor/src/extractors/hotel_config.py` and `extractor/src/database.py`.

---

## Entry Gate

- Locked SPEC available: `process/features/financials/active/financials_17-07-26/financials_SPEC_17-07-26.md`
- INNOVATE Decision Summary (GO verdict) available in umbrella plan context
- Phase 0 (this plan set) written

---

## Blast Radius

- `extractor/src/extractors/cashiering.py` (new)
- `extractor/src/database.py` (modified — add `insert_cashiering_postings()` method; `insert_raw_data()` is NOT reused)
- `extractor/src/main.py` (modified — wire `CashieringExtractor` into orchestration)
- `extractor/tests/` (new test files for the extractor + the pure window-chunking function)

---

## Implementation Checklist

### Step A — Research API shape and existing patterns

- [ ] A1. Read `docs/OPERA Cloud Cashiering API (26.2.0.0).json` for the `/financialPostings`
      endpoint — confirm response shape, pagination params (`limit`, `offset`/`hasMore`), and
      required path/query params (hotelId, date range).
- [ ] A2. Read `extractor/src/extractors/hotel_config.py` in full — note that `fetch_all()` is
      hardcoded to `reservations.reservationInfo[]` and is NOT reusable for cashiering.
      `CashieringExtractor` must use `fetch_one()` in a manual loop iterating on `hasMore`
      (see C2). Also note that `hotel_config.py` uses `len(chunk) < limit` as a safety fallback
      stop condition in addition to `hasMore` — mirror that safety fallback in the cashiering loop.
- [ ] A3. Read `extractor/src/database.py` — note that `insert_raw_data()` is hardcoded to
      `raw.booking_core_reservations` and is NOT reusable for cashiering. A new method
      `insert_cashiering_postings()` must be added to `database.py` (see D1/D2).
- [ ] A4. Read `extractor/src/client.py` and `extractor/src/main.py` to confirm how
      `ReservationExtractor`/`HotelConfigExtractor` are constructed and invoked, so
      `CashieringExtractor` matches the same constructor/interface shape.
- [ ] A5. Max limit for `/financialPostings` is **50** (confirmed from OPERA API docs — SPEC
      stated 4000 incorrectly; all checklist items and tests must use `limit=50`). Max date window
      is **30 days** (OPERA allows up to 30-day windows; SPEC stated 7 days incorrectly; use
      `window_days=30` as the default in `generate_date_windows()`).

### Step B — Pure window-chunking function

- [ ] B1. Implement `generate_date_windows(start: date, end: date, window_days: int = 30) -> list[tuple[date, date]]`
      as a pure, side-effect-free function (no I/O, no API calls) inside `cashiering.py` —
      inclusive windows of `window_days` length from `start` to `end`, self-correcting window
      count (do not hardcode a number of windows — let the function compute it from actual date
      arithmetic). Default `window_days=30`.
      **Note:** Function was previously named `generate_7day_windows` — the new name is
      `generate_date_windows` with a configurable `window_days` parameter.
- [ ] B2. Write unit tests for `generate_date_windows` covering: exact-multiple-of-window-days
      range, non-multiple range (partial final window), single-day range, start == end, start > end
      (should raise or return empty — decide and document), and the real backfill range
      (2026-01-01 to today) to confirm no off-by-one errors. Tests must use `window_days=30`
      as the default (not 7).

### Step C — CashieringExtractor class

- [ ] C1. Implement `CashieringExtractor` class in `extractor/src/extractors/cashiering.py`
      following the `HotelConfigExtractor` constructor/method shape (client, config, database
      dependencies injected the same way).
- [ ] C2. Implement the extraction loop: for each window from `generate_date_windows`, call
      `/financialPostings` with `limit=50` using `fetch_one()` (NOT `fetch_all()` — `fetch_all()`
      is hardcoded to reservations and is not reusable). Paginate manually: primary stop condition
      is `hasMore == False` in the response; secondary safety fallback stop condition is
      `len(page_results) < limit` (same safety pattern as hotel_config.py). Continue fetching
      pages within each window until one of the two stop conditions is met, accumulate all
      postings for that window.
- [ ] C3. Store ALL transaction types raw — Revenue, Payment, and Wrapper postings are all
      stored as-is in `raw.cashiering_postings`. Do NOT filter by `transactionType` during
      extraction. `transactionType` is a response field, not a query filter param — the OPERA API
      provides no Revenue-only filter. The dbt staging model in Phase 2 will apply the
      Revenue-only filter. Implement `raw_data` construction per posting: full JSONB `raw_data`
      column plus extracted top-level columns `transaction_no` (number/integer),
      `hotel_id`, `revenue_date`, `transaction_code`, `posted_amount` for indexing (per Decision Summary).
- [ ] C4. Add a unit test (mocked HTTP client, following the pattern in
      `extractor/tests/` for `ReservationExtractor`) confirming: `hasMore` is used as the primary
      pagination stop condition, `len(page_results) < limit` is used as the safety fallback stop,
      all windows in the backfill range are requested using `limit=50`, and extracted columns are
      correctly parsed from a sample OPERA `/financialPostings` response fixture that includes
      Revenue, Payment, and Wrapper postings.

### Step D — raw.cashiering_postings table + upsert

- [ ] D1. Add a new method `insert_cashiering_postings()` to `extractor/src/database.py`.
      Do NOT modify `insert_raw_data()` — it is hardcoded to `raw.booking_core_reservations`
      and must remain unchanged. The new method handles table creation for `raw.cashiering_postings`
      with columns: `transaction_no` (integer, PK/unique), `hotel_id`, `revenue_date`,
      `transaction_code`, `posted_amount`, `raw_data` (JSONB), plus standard `extracted_at`
      metadata column matching existing raw table conventions (do NOT add `updated_at` — existing
      tables use `extracted_at` only; the ON CONFLICT DO UPDATE sets extracted_at = NOW()).
- [ ] D2. Implement upsert in `insert_cashiering_postings()` using
      `ON CONFLICT (transaction_no) DO UPDATE` — `transaction_no` is type `number` in the OPERA
      API response (integer in Python); the ON CONFLICT clause uses `transaction_no`
      (snake_case column name after extraction). Do NOT use `insert_raw_data()` as the base —
      write `insert_cashiering_postings()` independently, mirroring the upsert pattern structure.
- [ ] D3. Add a test (mocked DB or test DB) confirming: inserting the same `transaction_no` twice
      does not create duplicate rows (idempotent re-run), and that a re-extraction with updated
      `raw_data` correctly overwrites the prior row (AC-9's dedup requirement made concrete).

### Step E — Orchestration wiring

- [ ] E1. Wire `CashieringExtractor` into `extractor/src/main.py` alongside the existing
      `ReservationExtractor` and `HotelConfigExtractor` calls — confirm run order does not matter
      (independent raw tables) or document if it does.
- [ ] E2. Confirm backfill start date (2026-01-01) is either a config value or a documented
      constant — do not hardcode it silently without a named constant/config entry.

---

## Exit Gate

```bash
cd extractor && poetry run pytest tests/ -v
# Expected: 0 failures; new cashiering extractor tests + generate_date_windows unit tests all pass

# Manual/agent-probe spot check (small date range against real or sandboxed OPERA Cloud creds if available)
cd extractor && poetry run python -m src
# Expected: raw.cashiering_postings populated; re-run does not duplicate rows (row count stable)
```

- All checklist items (A-E) checked
- `poetry run pytest tests/ -v` exits 0
- `raw.cashiering_postings` table exists with correct schema and upsert behavior verified
- Phase report written to report destination above

---

## Blockers That Would Justify BLOCKED Status

- OPERA Cloud `/financialPostings` endpoint behaves differently than documented (e.g. `hasMore`
  field absent or pagination differs from spec) — would require a VC-FEASIBILITY-PROBE before
  proceeding.
- No sandboxed/test OPERA Cloud credentials available to verify extraction against a live
  environment — extraction logic can still be unit-tested with mocks, but end-to-end verification
  would be blocked/deferred to a documented known-gap.
- Confirmed max limit is 50 (corrected from SPEC's 4000); if the API enforces a different limit
  than 50 at runtime, Step A5 would need re-confirmation before proceeding.

---

## Phase Loop Progress

Orchestrator reads this before deciding which subagent to spawn next. The canonical 7-step inner loop
`R -> I -> P -> PVL -> E -> EVL -> UP` SKIPS SPEC (SPEC runs once in the outer program loop, already locked).

- [x] 1. RESEARCH — research-agent: prior phase reports read; test context loaded; plan drift checked (2026-07-18)
- [x] 2. INNOVATE — innovate-agent: approach decided; Decision Summary written (2026-07-18)
- [x] 3. PLAN-SUPPLEMENT — plan-agent: existing phase plan updated; Inner Loop Refresh Note written (2026-07-18)
- [x] 4. PVL — vc-validate-agent: full V1-V7; validate-contract written (2026-07-18; inner-pvl: phase-01; Gate: CONDITIONAL — 2 concerns accepted)
- [x] 5. EXECUTE — all checklist items done; per-section test gates run and green (2026-07-18; 32/32 pytest pass, 16 new)
- [x] 6. EVL — all EVL gates green (32/32 pass; E2E: 18,245 postings confirmed, idempotency verified); EVL HANDOFF SUMMARY written (2026-07-18)
- [x] 7. UPDATE PROCESS — phase report written, umbrella state updated, commit done (2026-07-18)

**Validate-contract required before execute.** If step 4 (PVL) is unchecked or `## Validate Contract`
reads "(placeholder — vc-validate-agent writes this section before EXECUTE)", orchestrator must
spawn vc-validate-agent first. A partial contract missing Plan updates applied / Execute-agent
instructions / Test gates sections is treated as a placeholder.

---

## Touchpoints

- `extractor/src/extractors/cashiering.py` (new)
- `extractor/src/database.py` (modified — new `insert_cashiering_postings()` method added)
- `extractor/src/main.py` (modified)
- `extractor/tests/` (new test files)

---

## Public Contracts

- New `raw.cashiering_postings` table is a new contract consumed by Phase 2's staging model —
  column names/types set here are load-bearing for all downstream phases.
- No existing public contract is touched in this phase (purely additive new table + new module).

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| `generate_date_windows` unit tests (multiple/partial/edge ranges, window_days=30) | Fully-Automated | AC-9 (date-window chunking is pure, testable) |
| CashieringExtractor pagination stop-condition test (mocked HTTP, hasMore primary + len<limit fallback) | Fully-Automated | AC-9 (correct extraction windowing with hasMore + safety fallback) |
| Upsert idempotency test (duplicate transaction_no re-insert via insert_cashiering_postings) | Fully-Automated | AC-1 (transaction_no is the dedup key, integer type) |
| All transaction types stored raw (Revenue + Payment + Wrapper in fixture) | Fully-Automated | AC-9 (no extraction-time filter on transactionType) |
| Real/sandboxed extraction run against OPERA Cloud for a small date range | Agent-Probe | AC-1, AC-9 (end-to-end extraction works against real API shape) |

```bash
cd extractor && poetry run pytest tests/ -v
# Expected: 0 failures
```

---

## Resume and Execution Handoff

- Selected plan file path: `process/features/financials/active/financials_17-07-26/phase-01-cashiering-extractor_PLAN_17-07-26.md`
- Last completed step: PVL (Step 4) — inner-pvl validate-contract written 2026-07-18; Gate: CONDITIONAL
- Validate-contract status: CONDITIONAL (inner-pvl: phase-01; date 2026-07-18; 2 concerns accepted — see Validate Contract section)
- Next step: EXECUTE — spawn vc-execute-agent with this plan file path

---

## Test Infra Improvement Notes

(none identified yet)

---

## Validate Contract

Status: CONDITIONAL
Date: 18-07-26
date: 2026-07-18
generated-by: inner-pvl: phase-01
supersedes: 2026-07-17 (outer-pvl) — inner PVL has current evidence

Parallel strategy: sequential
Rationale: 2/7 signals (S2 schema/raw-table creation, S4 phase-program); sequential is correct for single-phase inner PVL re-validation

Plan updates applied:
- P1: Updated Step D1 to explicitly specify `extracted_at` only (no `updated_at`) — matches existing raw.booking_core_reservations convention in database.py
- P2: Clarified CashieringExtractor constructor needs both client + db injection — noted in execute-agent instructions E2
- P3 (2026-07-18 supplement): Corrected limit from 4000 to 50 throughout; renamed generate_7day_windows to generate_date_windows(window_days=30); updated A2/A3 to document that fetch_all() and insert_raw_data() are NOT reusable; updated C2 to use fetch_one() with hasMore as primary stop; updated C3 to store all transaction types raw; updated D1/D2 to use new insert_cashiering_postings() method; transactionNo confirmed as integer type for ON CONFLICT clause
- P4 (2026-07-18 inner-pvl): Added E6 instruction clarifying table creation location (inside insert_cashiering_postings(), not in setup()); Added E7 instruction correcting A2 cross-reference to hotel_config.py re hasMore pattern

Execute-agent instructions:
- E1: Use `extracted_at` only in raw.cashiering_postings schema — do NOT add `updated_at`. Existing tables (raw.booking_core_reservations) use `extracted_at` only; the `ON CONFLICT DO UPDATE SET extracted_at = NOW()` pattern is sufficient.
- E2: CashieringExtractor constructor requires both a client (BaseOperaClient) and a database (Database) parameter since it writes to raw.cashiering_postings. Reference ReservationExtractor pattern for the writing side, and HotelConfigExtractor for the API-calling side. The main.py wiring will need `cashiering_extractor = CashieringExtractor(client, db)`.
- E3: Define `BACKFILL_START_DATE = date(2026, 1, 1)` as a named constant at module level in cashiering.py — do not hardcode the date literal at the call site without a name.
- E4: Stop condition for pagination — use `hasMore == False` as the PRIMARY stop condition. Use `len(page_results) < limit` as a SECONDARY safety fallback (same safety pattern as hotel_config.py). Do NOT use `len < limit` alone as the primary stop. The unit test in C4 must include fixtures that exercise both stop paths. Use `limit=50` (not 4000 — OPERA API max is 50).
- E5: AC-10 (multi-page pagination) — ensure the extraction loop continues fetching pages within each date window until one of the two stop conditions is met: `hasMore == False` OR `len(page_results) < limit`. The unit test in C4 must include a two-page fixture (page 1 hasMore=True + 50 rows, page 2 hasMore=False + partial rows) to prove this. Also add a fixture where hasMore=True but len < 50 (edge case: hasMore=True but short page — safety fallback fires).
- E6: Table creation for raw.cashiering_postings goes INSIDE `insert_cashiering_postings()` as `CREATE TABLE IF NOT EXISTS raw.cashiering_postings (...)` + `CREATE UNIQUE INDEX IF NOT EXISTS` statements executed at the start of the method — do NOT add cashiering table creation to `setup()`. The method handles its own table setup on first call. Pattern: `CREATE TABLE IF NOT EXISTS raw.cashiering_postings (transaction_no INTEGER PRIMARY KEY, hotel_id TEXT, revenue_date DATE, transaction_code TEXT, posted_amount NUMERIC, raw_data JSONB NOT NULL, extracted_at TIMESTAMPTZ DEFAULT NOW())` at the top of insert_cashiering_postings(), before the INSERT statement. Also add `CREATE UNIQUE INDEX IF NOT EXISTS uq_cashiering_transaction_no ON raw.cashiering_postings (transaction_no)` if using a non-PK unique constraint approach.
- E7: When reading hotel_config.py in Step A2, note that hotel_config.py does NOT use `hasMore` as a stop condition — it uses only `len(chunk) < _PAGE_SIZE` (offset/limit pagination via the Room Config API, which does not return hasMore). The cashiering loop's `hasMore` primary stop condition instead mirrors the pattern in `client.fetch_all()` (which uses `hasMore` for reservations). Follow C2 for cashiering pagination logic; do not expect to find `hasMore` in hotel_config.py.

Test gates (C3 5-column table — ADDITIVE; existing consumers still parse the legacy line form below it):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| AC-9-windows | generate_date_windows produces correct non-overlapping windows for all edge cases (window_days=30 default) | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` (window unit tests: exact-multiple, partial, single-day, start==end, start>end, real 2026-01-01-to-today range) | A |
| AC-9-pagination | Extraction pagination: hasMore is primary stop; len(chunk) < limit is safety fallback | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` (mocked HTTP: hasMore=False stops fetch; hasMore=True + short page also stops via fallback) | A |
| AC-10-multipage | Extractor fetches all pages within a date window until hasMore=False OR len < limit | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` (mocked HTTP fixture: page 1 hasMore=True + 50 rows, page 2 hasMore=False + partial rows; assert total row count = 50 + partial) | A |
| AC-1-dedup | Re-inserting same transaction_no does NOT duplicate rows; updated raw_data overwrites prior row | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` (upsert idempotency test via insert_cashiering_postings: insert row, re-insert with modified raw_data, confirm row count = 1 and raw_data is updated) | A |
| AC-9-alltype | All transaction types (Revenue + Payment + Wrapper) stored raw without extraction-time filter | Fully-Automated | `cd extractor && poetry run pytest tests/ -v` (fixture with 3 posting types; assert all 3 stored in raw_data) | A |
| E2E-extraction | raw.cashiering_postings populated from real OPERA Cloud creds for a small date range | Agent-Probe | Run `cd extractor && poetry run python -m src` for a 30-day window; confirm row count > 0 and re-run confirms no row count increase | D |

gap-resolution legend:
- A — proven now (gate passes in this cycle)
- B — fixed in this plan (gate added by this plan's checklist)
- C — deferred to a named later phase/plan
- D — backlog test-building stub (named residual; keep-active; continue)

C-4 reconciliation: the `strategy:` column carries ONLY the 3 proving strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is NEVER a `strategy:` value — it is a named residual row carried via gap-resolution D, never a strategy that proves a behavior.

Legacy line form (retained so existing validate-contract consumers still parse):
- extractor/generate_date_windows: Fully-automated: `cd extractor && poetry run pytest tests/ -v`
- extractor/pagination: Fully-automated: `cd extractor && poetry run pytest tests/ -v`
- extractor/upsert: Fully-automated: `cd extractor && poetry run pytest tests/ -v`
- extractor/E2E: agent-probe: run extractor against real OPERA Cloud creds for small date range

Failing stub (AC-9-windows):
test("should generate correct non-overlapping 30-day windows for all edge cases", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: generate_date_windows edge case coverage (window_days=30)")
})

Failing stub (AC-9-pagination):
test("should stop pagination when hasMore is False (primary) or len(page) < limit (fallback)", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: pagination stop — hasMore primary + len<limit fallback")
})

Failing stub (AC-10-multipage):
test("should fetch all pages within a date window until stop condition met", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: multi-page extraction within a single window")
})

Failing stub (AC-1-dedup):
test("should not create duplicate rows when same transaction_no is inserted twice via insert_cashiering_postings", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: upsert idempotency on transaction_no")
})

Failing stub (AC-9-alltype):
test("should store Revenue, Payment, and Wrapper postings without extraction-time filtering", () => {
  throw new Error("NOT IMPLEMENTED — TDD stub: all transaction types stored raw")
})

Dimension findings:
- Infra fit: PASS — Python/psycopg2/Postgres stack proven; fetch_one() with params dict is valid for page-by-page pagination; respx + pytest-asyncio pattern confirmed from existing test suite; no new runtime dependencies
- Test coverage: PASS — 5 Fully-Automated pytest gates cover all core behaviors; E2E is Agent-Probe/gap-D (requires live OPERA creds, not in CI — documented known-gap)
- Breaking changes: CONCERN (accepted) — table creation location clarified via E6 instruction: CREATE TABLE IF NOT EXISTS goes inside insert_cashiering_postings() itself, not in setup(). Resolved: E6 provides explicit execute-agent instruction.
- Security surface: PASS — no auth/identity/billing/secrets surface changes; OAuth + x-app-key pattern unchanged; raw posting data stored in internal warehouse only

Section findings:
- Section A (Research API shape): CONCERN (accepted) — A2 incorrectly states hotel_config.py uses hasMore; actual hotel_config.py uses only len < _PAGE_SIZE (Room Config API has no hasMore field). Cashiering hasMore pattern mirrors client.fetch_all(). Resolved: E7 corrects this for execute-agent.
- Section B (Window function): PASS — generate_date_windows is pure, testable, default window_days=30 is correct
- Section C (CashieringExtractor): PASS — fetch_one() accepts params dict and works with offset pagination; C2 specification is mechanically implementable; constructor with client + db injection explicitly documented in E2
- Section D (DB + upsert): PASS — insert_cashiering_postings() is additive; ON CONFLICT (transaction_no) DO UPDATE is standard pattern; mocked-DB limitation already documented
- Section E (Orchestration): PASS — main.py wiring is straightforward; BACKFILL_START_DATE constant approach documented in E3

Structural note (phase-stub plan shape):
validate-plan-artifact.mjs reports 4 FAILs + 4 warnings. These are expected structural differences for a phase-stub plan (Complexity at umbrella level, Exit Gate = Phase Completion Rules, Acceptance Criteria in SPEC, Purpose = overview section). Not content gaps that block EXECUTE.

Open gaps:
- E2E extraction against real OPERA Cloud: known-gap: documented as Agent-Probe — requires live/sandboxed OPERA credentials not available in automated test suite

What this coverage does NOT prove:
- AC-9-windows: Does not prove the OPERA API actually enforces a 30-day span limit at runtime (confirmed from OPERA API docs; no automated re-verification in CI)
- AC-9-pagination: Does not prove actual OPERA API response field names match the mock fixture (relies on OPERA Cashiering spec for field names: transactionNo, revenueDate, transactionCode, postedAmount, hasMore)
- AC-10-multipage: Does not prove the OPERA API actually returns hasMore=True for pages beyond the first
- AC-1-dedup: Mocked DB test does not prove the PostgreSQL ON CONFLICT clause works against a real DB instance (requires live Postgres for full hybrid verification)
- AC-9-alltype: Does not prove OPERA API returns all three transaction types for any given hotel/date range
- E2E-extraction: Not run in CI; depends on analyst with OPERA Cloud access running manually

Gate: CONDITIONAL
Accepted by: session (autonomous, /goal execution) — concerns accepted: (1) Breaking changes: table creation location clarified via E6 instruction; (2) Section A: hotel_config.py hasMore cross-reference inaccuracy corrected via E7 instruction

---

## Inner Loop Refresh Note

**Date:** 2026-07-18
**Changed by:** vc-plan-agent (PVL-supplement / inner-loop refresh — research findings incorporated)

**Summary of changes:** 7 research corrections applied — max limit corrected to 50 (was 4000), window function renamed to `generate_date_windows(window_days=30)` (was `generate_7day_windows`), `fetch_all()`/`insert_raw_data()` documented as non-reusable (cashiering must use `fetch_one()` loop + new `insert_cashiering_postings()` method), `hasMore` designated as primary pagination stop condition (len<limit as safety fallback), all transaction types stored raw (no extraction-time filter), `transactionNo` confirmed as integer type for ON CONFLICT. Validate-contract E4/E5 instructions and all test gates updated accordingly. Re-run PVL from V1 before EXECUTE.
