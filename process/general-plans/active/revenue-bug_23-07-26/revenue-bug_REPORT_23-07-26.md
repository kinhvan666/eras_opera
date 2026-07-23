# Bug Investigation Report: OPERA Revenue Discrepancy (July 2026)

## Executive Summary
**Issue:** The Total Revenue dashboard is reporting 3.79B instead of the 3.55B OPERA Manager Report for July 2026 (an overstatement of ~240M).
**Root Cause:** The `stg_cashiering_postings.sql` DBT model attempts to filter out Taxes and Service Charges by checking `t.classification in ('Tax', 'ServiceCharge')`. However, `t.classification` (extracted from the OPERA API in `stg_transaction_codes.sql`) is a full JSON object string (e.g., `{"type": "Revenue", "transactionType": {"code": "Tax"}}`). Because a JSON string never exactly equals `'Tax'`, the exclusion fails, causing ~240M in taxes to be improperly included in `net_amount` and miscategorized in `revenue_category`.

## Technical Analysis
1. **Schema Verification:** According to the OPERA Cloud API docs (`docs/OPERA Cloud Front Desk Configuration API (26.2.0.0).json`), the `classification` field inside `hotelTransactionCodeType` is a `$ref` to `trxCodeClassificationType`, which is a complex JSON object.
2. **Data Extraction Flaw:** In `eras_dbt/models/staging/stg_transaction_codes.sql` (Line 37), the `classification` is extracted using `tc->>'classification'`. This correctly pulls the object, but casts it to a literal JSON string in Postgres.
3. **Filtering Failure:** In `stg_cashiering_postings.sql`, the calculation for `net_amount` explicitly checks `t.classification in ('Tax', 'ServiceCharge')`. This always evaluates to `FALSE`. 
4. **Fallback Escape:** While `s.transaction_code like '7%'` catches most standard taxes, any tax or service charge on non-standard codes (e.g., `2010`) falls back to the classification check, fails the exact string match, and erroneously adds its `posted_amount` to the revenue `net_amount`. 

## Actionable Recommendations
- Apply the fix boundary to `stg_cashiering_postings.sql` so that it parses the stringified JSON for the transaction type code using `LIKE '%"Tax"%'` or Postgres `jsonb` path functions.
- The same logic applies to `revenue_category`, which should map the internal enum values (`"Lodging"`, `"FoodAndBeverage"`, `"Tax"`) to the dashboard-friendly values (`Room`, `FnB`, `Tax`, etc.) instead of passing the raw JSON object string to the frontend.

```
FIX BOUNDARY:
affected_files: [eras_dbt/models/staging/stg_cashiering_postings.sql]
root_cause: `t.classification` from the API is stored as a JSON string, causing exact string matches `in ('Tax', 'ServiceCharge')` to silently fail. This allows tax amounts to leak into `net_amount`.
proposed_fix: Replace `t.classification in ('Tax', 'ServiceCharge')` and `when t.classification is not null then t.classification` with JSON-aware checks (e.g., `when t.classification like '%"Tax"%' then 'Tax'`) to accurately evaluate the nested classification.
risk_class: medium
```
