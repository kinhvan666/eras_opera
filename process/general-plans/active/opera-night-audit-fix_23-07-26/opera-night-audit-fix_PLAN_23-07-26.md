# Implementation Plan: OPERA Night Audit Fix

**TL;DR:** Modify `HotelConfigExtractor` to fetch the hotel's `businessDate` from the API and use it to bound cashiering data extraction in `main.py` instead of the system's current date.

## Context
OPERA determines the End of Day by rolling the `businessDate` forward. Cashiering postings extraction needs to fetch data only up to `business_date - 1` to ensure we do not fetch partial un-audited data for the current business date. This fixes the issue of night audit races.

## Touchpoints
- `extractor/src/extractors/hotel_config.py` — Add `fetch_business_date` method.
- `extractor/src/main.py` — Update cashiering postings date boundary logic.

## Public Contracts
- `HotelConfigExtractor.fetch_business_date(self) -> date` (or `str`) — New method that calls `GET /hotels/{hotelId}/businessDate` (with the appropriate API version prefix if required by the OPERA API).

## Blast Radius
- **Risk Class:** Low
- **Scope:** 2 files in the `extractor` package. Modifying the date boundary for cashiering backfill.

## Implementation Steps

### Step 1: Add `fetch_business_date` in `HotelConfigExtractor`
- In `extractor/src/extractors/hotel_config.py`:
- Import `datetime` if needed to return a `date` object, or just return a parsed ISO date.
- Add a new async method `fetch_business_date(self) -> datetime.date`.
- The method should make a GET request to `/hotels/{settings.opera_hotel_id}/businessDate` (or whatever specific module prefix OPERA uses for this endpoint).
- Extract the date from the response JSON and parse it into a `datetime.date` object.

### Step 2: Update `main.py` to use `businessDate`
- In `extractor/src/main.py`:
- Call `business_date = await hotel_extractor.fetch_business_date()` early in the `run()` function or right before the cashiering logic.
- Replace `yesterday = date.today() - timedelta(days=1)` with `yesterday = business_date - timedelta(days=1)`.
- Use this new `yesterday` bound for the `cashiering_extractor.fetch_postings(...)` call.
- Add a log message indicating the fetched business date.

## Verification Evidence
| Gate / Scenario | Strategy | Proves SPEC criterion |
| --- | --- | --- |
| System date vs Business date | Agent-Probe | Cashiering sync properly uses `businessDate - 1` instead of system date |
| Fetch business date success | Fully-Automated | `fetch_business_date` correctly parses the API response |

## Test Infra Improvement Notes
(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Resume and Execution Handoff
- **Plan File:** `process/general-plans/active/opera-night-audit-fix_23-07-26/opera-night-audit-fix_PLAN_23-07-26.md`
- **Last completed phase:** Plan creation
- **Validate-contract status:** pending
- **Context files loaded:** `extractor/src/extractors/hotel_config.py`, `extractor/src/main.py`
- **Next step:** Run `vc-validate-agent` (if applicable) and switch to EXECUTE mode to implement Step 1 and Step 2.
