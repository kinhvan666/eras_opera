---
name: plan:cashiering-backfill
description: Re-run CashieringExtractor full backfill + dbt rebuild + verify gap 784→<784
date: 20-07-26
feature: financials
phase: "standalone"
---

# Cashiering Backfill Re-run Plan

Complexity: SIMPLE  
Status: EXECUTED (COMPLETE_WITH_GAPS)  
Date: 2026-07-20
Executed: 2026-07-20 — re-run extract + dbt rebuild; gap stayed 784 (OPERA API miss confirmed); see cashiering-backfill_REPORT_20-07-26.md 
**Feature:** financials  
**Scope:** Bước 1 từ handout — re-run extractor, rebuild dbt, verify gap giảm

---

## Overview

Gap hiện tại: 784 CheckedOut stays trong `fct_reservation_night` không có row nào trong `fct_folio_line`.
Root cause: CashieringExtractor bỏ sót khi backfill ban đầu (pagination/timeout, rải đều 7 tháng).

Plan này thực hiện:
1. Chụp baseline counts trước khi chạy
2. Re-run CashieringExtractor (full backfill 2026-01-01 → today)
3. Verify raw rows tăng
4. Rebuild dbt staging + dimensional layers
5. Verify gap giảm, report gap còn lại

**Không làm trong plan này:** OPERA API investigation, root cause điều tra 772 stays trắng, viết dbt tests mới.

---

## Duplicate Risk Assessment

**Risk: NONE.**

`database.py:insert_cashiering_postings` dùng:
```sql
ON CONFLICT (transaction_no) DO UPDATE SET ...
```
`transaction_no INTEGER PRIMARY KEY` là PK của `raw.cashiering_postings`. Re-run extractor cho cùng postings chỉ UPDATE — không INSERT thêm duplicate row. Việc check `transaction_no` uniqueness trước khi chạy là advisory (để confirm baseline), không phải safety gate.

---

## Touchpoints

- `extractor/src/extractors/cashiering.py` — `CashieringExtractor`, `BACKFILL_START_DATE = date(2026, 1, 1)`
- `extractor/src/client.py` — `fetch_one` với `@retry(5)`, `_fetch_page` riêng để retry không reset pagination
- `extractor/src/database.py` — `insert_cashiering_postings` (upsert on transaction_no)
- `extractor/src/main.py` — entry point; cashiering chạy sau reservations trong cùng 1 run
- `eras_dbt/models/staging/stg_cashiering_postings.sql` — staging layer
- `eras_dbt/models/dimensional/fct_folio_line.sql` — fact table

---

## Public Contracts

Không thay đổi schema, API, hay interface nào. Plan này chỉ re-run extraction + dbt build.

---

## Blast Radius

- **Files modified:** 0 source files thay đổi
- **Data touched:** `raw.cashiering_postings` (upsert), `analytics.stg_cashiering_postings`, `analytics.fct_folio_line` (rebuild)
- **Risk class:** LOW — idempotent upsert + dbt rebuild
- **Rollback:** Không cần — upsert không xóa data cũ; dbt build có thể re-run lại bất cứ lúc nào

---

## Implementation Checklist

### Pre-run: Chụp baseline

**Step 1 — Record baseline raw row count**
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c \
  "SELECT COUNT(*) AS total_raw_rows, COUNT(DISTINCT transaction_no) AS distinct_txn_nos FROM raw.cashiering_postings;"
```
Ghi lại kết quả. Dự kiến: ~18,245 rows (từ handout ngày 17-07).

**Step 2 — Record baseline distinct reservation_id trong raw**
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c \
  "SELECT COUNT(DISTINCT raw_data->>'reservationId') AS distinct_reservation_ids FROM raw.cashiering_postings;"
```
Ghi lại kết quả để so sánh sau khi re-run.

**Step 3 — Record baseline gap count**
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "
SELECT COUNT(*) AS gap_stays
FROM analytics.fct_reservation_night frn
LEFT JOIN analytics.fct_folio_line ffl ON ffl.reservation_id = frn.reservation_id
WHERE frn.status = 'CheckedOut'
  AND frn.departure_date <= '2026-07-18'
  AND ffl.reservation_id IS NULL
GROUP BY frn.reservation_id
HAVING COUNT(frn.reservation_id) > 0
;"
```
Nếu query trả về nhiều rows (một row per stay), chạy thêm:
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "
SELECT COUNT(DISTINCT frn.reservation_id) AS gap_stays
FROM analytics.fct_reservation_night frn
LEFT JOIN analytics.fct_folio_line ffl ON ffl.reservation_id = frn.reservation_id
WHERE frn.status = 'CheckedOut'
  AND frn.departure_date <= '2026-07-18'
  AND ffl.reservation_id IS NULL
;"
```
Ghi lại. Dự kiến: ~772 (sau khi 12 stays đã có data từ lần chạy trước).

---

### Run: Extractor

**Step 4 — Re-run CashieringExtractor (full backfill)**

Chạy từ thư mục `extractor/`:
```bash
cd D:/ErasProjects/ErasOpera/extractor && poetry run python -m src
```

Hoặc từ repo root:
```bash
cd D:/ErasProjects/ErasOpera && cd extractor && poetry run python -m src
```

Extractor sẽ:
- Fetch hotel config, reservations (90 ngày gần nhất)
- Fetch cashiering postings từ `BACKFILL_START_DATE = 2026-01-01` đến `date.today()`
- In ra: `"Fetching cashiering postings from 2026-01-01 to today..."` và `"Fetched N cashiering postings."`
- Upsert vào `raw.cashiering_postings` (ON CONFLICT DO UPDATE — an toàn với re-run)

**Quan sát stdout:**
- Nếu `N > 18245` (hoặc > baseline đã ghi) → extractor đã lấy thêm postings mới
- Nếu `N ≈ baseline` → OPERA API không trả thêm data cho 772 stays đó (extraction-level miss)
- Nếu gặp lỗi `OperaAuthError` → check env vars OAuth; `DatabaseConnectionError` → check Docker

**Step 5 — Verify raw rows tăng**
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c \
  "SELECT COUNT(*) AS total_raw_rows, COUNT(DISTINCT transaction_no) AS distinct_txn_nos FROM raw.cashiering_postings;"
```
So sánh với baseline (Step 1). Nếu tăng → extractor đã lấy được thêm data.

```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c \
  "SELECT COUNT(DISTINCT raw_data->>'reservationId') AS distinct_reservation_ids FROM raw.cashiering_postings;"
```
So sánh với baseline (Step 2).

---

### Rebuild: dbt

**Step 6 — dbt build**

Chạy từ thư mục `eras_dbt/`:
```bash
cd D:/ErasProjects/ErasOpera/eras_dbt && dbt build --profiles-dir .
```

Lệnh này rebuild toàn bộ staging + dimensional models, bao gồm:
- `stg_cashiering_postings` — re-read từ `raw.cashiering_postings` (đã có data mới)
- `fct_folio_line` — rebuild từ staging

Nếu chỉ muốn rebuild cashiering-related models (nhanh hơn):
```bash
cd D:/ErasProjects/ErasOpera/eras_dbt && dbt build --select stg_cashiering_postings fct_folio_line --profiles-dir .
```

Chờ dbt in `Finished running N models` — không có lỗi.

---

### Verify: Gap giảm

**Step 7 — Re-run gap query**
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "
SELECT COUNT(DISTINCT frn.reservation_id) AS gap_stays
FROM analytics.fct_reservation_night frn
LEFT JOIN analytics.fct_folio_line ffl ON ffl.reservation_id = frn.reservation_id
WHERE frn.status = 'CheckedOut'
  AND frn.departure_date <= '2026-07-18'
  AND ffl.reservation_id IS NULL
;"
```

**Expected outcomes:**
- `gap_stays < 784` → backfill có tác dụng
- `gap_stays ≈ 772` → 12 stays mới nhất đã được cover, 772 stays còn lại thực sự không có data trong OPERA API
- `gap_stays = 784` (hoặc ≈ baseline) → dbt chưa rebuild xong, hoặc OPERA API thực sự không trả thêm data

**Step 8 — Report gap còn lại**

Nếu gap > 0 sau khi rebuild, chạy để biết phân bố theo tháng:
```bash
docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "
SELECT
  DATE_TRUNC('month', frn.departure_date)::date AS month,
  COUNT(DISTINCT frn.reservation_id) AS gap_stays
FROM analytics.fct_reservation_night frn
LEFT JOIN analytics.fct_folio_line ffl ON ffl.reservation_id = frn.reservation_id
WHERE frn.status = 'CheckedOut'
  AND frn.departure_date <= '2026-07-18'
  AND ffl.reservation_id IS NULL
GROUP BY 1
ORDER BY 1
;"
```

Ghi lại kết quả. Kết quả này quyết định có cần Bước 2 (OPERA API investigation) từ handout hay không.

---

## Acceptance Criteria

1. Extractor chạy xong không có exception trong stdout/stderr
2. `raw.cashiering_postings` row count sau ≥ row count trước (upsert không giảm)
3. dbt build hoàn thành với 0 errors (warnings chấp nhận được)
4. Gap count sau < Gap count trước (ít nhất -12 từ 12 stays đã có raw data mới)
5. Gap report theo tháng đã được ghi lại để quyết định Bước 2

**Definition of DONE:** Bước này done khi gap ≤ 772. Nếu gap vẫn = 784 sau dbt rebuild → investigate xem dbt có thực sự rebuild `fct_folio_line` chưa trước khi kết luận.

---

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| raw row count sau ≥ baseline | Hybrid (requires Postgres container) | Extractor re-run thành công, upsert hoạt động đúng |
| distinct reservation_ids trong raw tăng hoặc bằng | Hybrid (requires Postgres container) | Extractor fetch được thêm postings cho các stays bị thiếu |
| dbt build exits 0 | Hybrid (requires dbt + Postgres) | Staging + fact layers đã rebuild với data mới |
| gap_stays sau < 784 | Hybrid (requires Postgres, analytics schema) | Gap giảm — backfill có tác dụng |
| gap report theo tháng được ghi lại | Agent-probe (judge output) | Đủ thông tin để quyết định Bước 2 |

---

## Test Infra Improvement Notes

(none identified yet — plan là operational re-run, không thêm test infrastructure)

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| OPERA API vẫn không trả data cho 772 stays | HIGH (confirmed từ handout) | Expected outcome — report gap còn lại để escalate lên Bước 2 |
| Token expiry giữa chừng | LOW | `_get_token()` fetch once per run; nếu lỗi → re-run |
| dbt model reference error | LOW | dbt build --select để test riêng nếu full build fail |
| Docker container không chạy | LOW | Kiểm tra `docker ps` trước Step 4 |

---

## Resume and Execution Handoff

 1. **Selected plan file path:** `process/features/financials/active/financials_17-07-26/cashiering-backfill_PLAN_20-07-26.md`
 2. **Last completed phase/step:** EXECUTE (done 2026-07-20; gap stayed 784 — OPERA API miss confirmed)
3. **Validate-contract status:** pending (vc-validate-agent writes this section)
4. **Supporting context files loaded:**
   - `extractor/src/extractors/cashiering.py` (BACKFILL_START_DATE, fetch logic)
   - `extractor/src/client.py` (retry, fetch_one)
   - `extractor/src/database.py` (upsert on transaction_no)
   - `extractor/src/main.py` (entry point, cashiering integration)
   - `process/features/financials/active/financials_17-07-26/cashiering-extraction-gap_HANDOUT_20-07-26.md`
5. **Next step for fresh agent:** Chạy Steps 1-3 (baseline), rồi Step 4 (extractor), rồi Steps 5-8 (verify). Container: `erasopera-postgres-1`, port `5434`, db `erg_opera_data`, role `user`.

---

## Phase Completion Rules

This plan is SIMPLE (single execution session). A phase/step is COMPLETE only when:

1. Command runs without exception in stdout/stderr
2. Database counts are verified with explicit before/after numbers
3. dbt build exits 0 with no model errors
4. Gap count verified and recorded

Status markers used:
- ⏳ PLANNED — not started
- 🔨 CODE DONE — command run, output not yet verified
- ✅ VERIFIED — verified with database query or command output
- 🚧 BLOCKED — issue preventing completion

---

## Validate Contract

Status: PASS
Date: 20-07-26
date: 2026-07-20
generated-by: outer-pvl

Parallel strategy: sequential
Rationale: 3 signals dominant — single execution session, no cross-agent coordination, deterministic operational re-run (0 file changes). Sequential extractor→dbt→verify is the only correct ordering.

Test gates (C3 5-column table — ADDITIVE):

| criterion id | behavior | strategy | proving test | gap-resolution |
|---|---|---|---|---|
| TC1 | Extractor re-run completes without exception | Hybrid | `cd extractor && poetry run python -m src` then stdout shows "Fetched N cashiering postings." with no OperaAuthError/DatabaseConnectionError | A |
| TC2 | raw.cashiering_postings row count after >= baseline (upsert non-destructive) | Hybrid | `docker exec erasopera-postgres-1 psql -U user -d erg_opera_data -c "SELECT COUNT(*), COUNT(DISTINCT transaction_no) FROM raw.cashiering_postings;"` before vs after | A |
| TC3 | dbt build exits 0, no model errors | Hybrid | `cd eras_dbt && dbt build --profiles-dir .` shows "Finished running N models" with 0 errors | A |
| TC4 | Gap (CheckedOut stays missing folio) decreases after rebuild | Hybrid | gap query COUNT(DISTINCT frn.reservation_id) WHERE status='CheckedOut' AND departure<=2026-07-18 AND ffl.reservation_id IS NULL — before vs after | A |
| TC5 | Distinct reservation_ids in raw increases or holds | Hybrid | `SELECT COUNT(DISTINCT raw_data->>'reservationId') FROM raw.cashiering_postings;` before vs after | A |

Legacy line form:
- Infra fit: Hybrid: docker ps + psql connectivity pre-check | extractor run | dbt build — all pass
- Test coverage: Hybrid: before/after count queries prove gap reduction | Agent-probe: interpret residual gap distribution by month
- Breaking changes: none — idempotent upsert on transaction_no PK, 0 source files changed
- Security surface: none — no new auth surface, reuses existing OAuth env

Dimension findings:
- Infra fit: PASS — Postgres container `erasopera-postgres-1:5434`, db `erg_opera_data` confirmed reachable in handout; extractor + dbt already proven operational (Plan A–C done 19-07)
- Test coverage: PASS — 5 before/after hybrid gates cover extract→raw→staging→fact→gap loop; residual gap distribution is agent-probe (judgement)
- Breaking changes: PASS — 0 files modified; ON CONFLICT (transaction_no) DO UPDATE makes re-run idempotent (no duplicate rows)
- Security surface: PASS — no new credentials, endpoints, or auth paths; reuses existing OPERA OAuth + PG connection

Open gaps:
- 772 stays (post re-run) likely still missing folio — handout confirms HIGH likelihood OPERA API does not return postings for this layer. Out of scope for this plan (Step 1 only); escalates to handout Bước 2 (OPERA API investigation) as a NEW PLAN.

What this coverage does NOT prove:
- TC1 does not prove OPERA API will actually return additional postings for the 772 missing stays (extraction-level miss is the suspected root cause; re-run may yield N ≈ baseline)
- TC4 does not prove gap reaches 0 — expected outcome is gap ≤ 772, not 0; residual gap needs separate API investigation
- TC2/TC5 do not prove postings are correctly attributed to the right reservation_id (267 raw rows have null reservationId.id — known unrecoverable join loss, noted in handout Bước 3)
- Agent-probe gap-by-month report classifies residual distribution but does not diagnose root cause

Gate: PASS (no FAILs, plan structure valid, all touchpoints resolve)
Accepted by: session (autonomous validate for operational re-run)

## Autonomous Goal Block

Goal: Reduce the Cashiering folio coverage gap (784 → ≤772 CheckedOut stays missing `fct_folio_line` rows) by re-running CashieringExtractor full backfill and rebuilding dbt staging + dimensional layers.
Scope: Operational re-run only — no source code changes.
Evidence gate: raw row count non-decreasing + gap_stays after < 784 + dbt build exits 0.
Out-of-scope: OPERA API root-cause investigation for residual gap, 267 null-reservationId recovery, new dbt data-quality tests (deferred to follow-up plan per handout Bước 2–4).
