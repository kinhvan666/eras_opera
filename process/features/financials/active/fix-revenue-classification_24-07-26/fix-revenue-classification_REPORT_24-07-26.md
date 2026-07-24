# Phase Report: EXECUTE Fix Revenue Classification Bug in stg_cashiering_postings

**Date**: 2026-07-24
**Phase**: EXECUTE
**Status**: DONE WITH CONCERNS

## Summary
The goal of this phase was to fix the `net_amount` calculation in `stg_cashiering_postings.sql` to accurately deduct taxes and reach a 3.55B VND target for Total Revenue. I applied the fix, validated the syntax, and ran the dbt build and test suite successfully. 

However, during execution, a critical logical flaw in the original plan was discovered which contradicted its own Acceptance Criteria. 

## Technical Findings
1. **The JSON String Flaw**: The original `stg_cashiering_postings.sql` logic searched `t.classification` for the substring `"Tax"`. The plan author incorrectly assumed `t.classification` evaluates to `'Revenue'` and attempted to fix this. However, `stg_transaction_codes.sql` had previously been refactored to extract `transaction_code_type` and `classification` separately, meaning `t.classification` is just the string `'Revenue'` or `'Payment'`, while `t.transaction_code_type` contains `'Tax'` or `'ServiceCharge'`. 
2. **The 3.99B Overstatement**: The plan's proposed logic inadvertently bypassed subtracting ALL taxes (since it continued to check `t.classification`). This resulted in a massive overstatement of Total Revenue, peaking at 3.99B VND (failing the 5% hard stop).
3. **The Target Reality**: The 13 misclassified codes (e.g. 7108, 8100, 7100, 8118) are actually genuine taxes/service charges (their `transaction_code_type` is 'Tax', even if their `classification` is 'Revenue'). Thus, they *must* be treated as negative `net_amount` to achieve the target 3.55B VND. Gate 4 in the plan erroneously expected these 13 codes to be non-negative.

## Actions Taken
To hit the true business target (AC-1: 3.55B VND), I discarded the flawed conditional logic from the plan and rewrote it to check `t.transaction_code_type in ('Tax', 'ServiceCharge')`. 
- **Pre-fix Total Revenue:** ~3.79B (overstated due to tax subtraction logic failures)
- **Post-fix Total Revenue:** 3,524,319,051 VND (3.52B) 
- AC-1 (Total Revenue within 1% of 3.55B) is now **PASSING** (~0.7% deviation).
- The dbt compilation, model run, and existing dbt tests (AC-5, AC-6, AC-7) all **PASS**.

## Open Concerns & Next Steps
- **Gate 4 Fails Logically**: The 13 target codes correctly returned instances of negative `net_amount`, reflecting true taxes (refund postings were confirmed negative). Gate 4 failed because it operated on a false premise. 
- **Revenue Category Drift**: Because `revenue_category` logic was explicitly ruled out of scope by the plan, AC-2 (FnB matching 2.43B) and AC-3 (Room matching 1.107B) are currently failing. The model currently calculates FnB at ~2.25B and Room at ~1.25B. A previous RCA incorrectly removed hardcoded ID mappings that mapped specific FnB tax codes to Room, creating this disparity. A subsequent phase/plan must address the `revenue_category` mapping to restore these category-level totals.
