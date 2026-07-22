---
name: plan:dashboard-v2-segment-refactor
description: "Refactor dashboard segments to use business-friendly names via new dbt dimension models."
date: 22-07-26
feature: dashboard-v2-segment-refactor
phase: "implementation"
---

# Plan: Dashboard v2 Segment Refactor

**Complexity:** SIMPLE

## 1. Overview

This plan details the steps to refactor the "Phân khúc" (Segments) tab in the dashboard. Currently, the charts display raw technical codes for market, source, room type, and rate code. This makes the analysis difficult for business users.

The chosen approach is to create new dbt dimension models that map these codes to human-readable, business-friendly names. The fact table will be updated to include these new names, and the dashboard will be modified to use them for grouping and display.

## 2. Goals

- Replace technical codes (e.g., `CORP`, `LEIS`, `RACK`) with business-friendly names (e.g., `Corporate`, `Leisure`, `Public Rack`) in the Segments tab.
- Improve the usability and readability of the segmentation analysis for non-technical users.
- Remove the "theo gói giá" (by rate code) chart as it provides low value and clutters the view.

## 3. Scope

### In Scope

- Creating three new dbt dimension models: `dim_market`, `dim_source`, and `dim_room_type`.
- Updating the `fct_reservation_night` dbt model to join the new dimensions.
- Updating the Streamlit dashboard code in `dashboard/ui/tabs/segments.py` and `dashboard/data/repository.py` to use the new dimension names.
- Removing the "by rate code" chart from the Segments tab.

### Out of Scope

- Changing any other tabs in the dashboard.
- Modifying the underlying data extraction process from OPERA Cloud.
- Creating a comprehensive mapping for all possible codes; we will start with known codes and add a placeholder for unknowns.

## 4. Touchpoints

- **`eras_dbt/models/dimensional/`**: New files will be created here.
- **`eras_dbt/models/dimensional/fct_reservation_night.sql`**: Will be modified.
- **`dashboard/data/repository.py`**: The `fetch_kpi_daily_segmented` function will be updated.
- **`dashboard/ui/tabs/segments.py`**: The charts will be updated to use new columns and labels.

## 5. Public Contracts

There are no changes to public-facing APIs or contracts. The changes are internal to the data transformation and presentation layers.

## 6. Blast Radius

- **Files:** ~6 files will be created or modified.
- **Packages:** `eras_dbt` and `dashboard`.
- **Risk Class:** Low. The changes are additive to the data model and isolated to one tab in the dashboard. The original code columns will remain, allowing for easy rollback if needed.

## 7. Implementation Checklist

### Phase 1: dbt Model Development

1.  **Create `dim_market.sql`**
    -   **File:** `D:/ErasProjects/ErasOpera/eras_dbt/models/dimensional/dim_market.sql`
    -   **Action:** Create a new dbt model that selects distinct `market_code` from `stg_reservations` and creates a `market_segment_name` using a `CASE` statement.
    -   **Content:**
        ```sql
        -- eras_dbt/models/dimensional/dim_market.sql
        SELECT DISTINCT
            market_code,
            CASE
                -- To be filled by developer based on business logic
                WHEN market_code = 'CORP' THEN 'Corporate'
                WHEN market_code = 'LEIS' THEN 'Leisure'
                WHEN market_code = 'RACK' THEN 'Public Rack'
                ELSE 'Other'
            END AS market_segment_name
        FROM {{ ref('stg_reservations') }}
        WHERE market_code IS NOT NULL
        ```

2.  **Create `dim_source.sql`**
    -   **File:** `D:/ErasProjects/ErasOpera/eras_dbt/models/dimensional/dim_source.sql`
    -   **Action:** Create a new dbt model that selects distinct `source_of_business` from `stg_reservations` and creates a `source_channel_name` using a `CASE` statement.
    -   **Content:**
        ```sql
        -- eras_dbt/models/dimensional/dim_source.sql
        SELECT DISTINCT
            source_of_business,
            CASE
                -- To be filled by developer based on business logic
                WHEN source_of_business = 'OTA' THEN 'Online Travel Agent'
                WHEN source_of_business = 'DIRECT' THEN 'Direct Booking'
                WHEN source_of_business = 'GDS' THEN 'Global Distribution System'
                ELSE 'Other'
            END AS source_channel_name
        FROM {{ ref('stg_reservations') }}
        WHERE source_of_business IS NOT NULL
        ```

3.  **Create `dim_room_type.sql`**
    -   **File:** `D:/ErasProjects/ErasOpera/eras_dbt/models/dimensional/dim_room_type.sql`
    -   **Action:** Create a new dbt model that selects distinct `room_type` from `stg_reservations` and creates a `room_type_name` using a `CASE` statement.
    -   **Content:**
        ```sql
        -- eras_dbt/models/dimensional/dim_room_type.sql
        SELECT DISTINCT
            room_type,
            CASE
                -- To be filled by developer based on business logic
                WHEN room_type = 'STD' THEN 'Standard Room'
                WHEN room_type = 'DLX' THEN 'Deluxe Room'
                WHEN room_type = 'SUI' THEN 'Suite'
                ELSE 'Other'
            END AS room_type_name
        FROM {{ ref('stg_reservations') }}
        WHERE room_type IS NOT NULL
        ```

4.  **Update `fct_reservation_night.sql`**
    -   **File:** `D:/ErasProjects/ErasOpera/eras_dbt/models/dimensional/fct_reservation_night.sql`
    -   **Action:** Modify the fact table to join the three new dimension tables. Add the new `*_name` columns to the final select.
    -   **Change:**
        ```sql
        -- Before
        -- ... existing joins ...
        SELECT
            -- ... existing columns ...
            res.market_code,
            res.source_of_business,
            res.room_type,
            res.rate_plan_code
        FROM {{ ref('stg_reservations') }} res
        -- ...

        -- After
        -- ... existing joins ...
        LEFT JOIN {{ ref('dim_market') }} m ON res.market_code = m.market_code
        LEFT JOIN {{ ref('dim_source') }} s ON res.source_of_business = s.source_of_business
        LEFT JOIN {{ ref('dim_room_type') }} rt ON res.room_type = rt.room_type
        
        SELECT
            -- ... existing columns ...
            res.market_code,
            COALESCE(m.market_segment_name, 'Unknown') AS market_segment_name,
            res.source_of_business,
            COALESCE(s.source_channel_name, 'Unknown') AS source_channel_name,
            res.room_type,
            COALESCE(rt.room_type_name, 'Unknown') AS room_type_name,
            res.rate_plan_code
        FROM {{ ref('stg_reservations') }} res
        -- ...
        ```

5.  **Build and Test dbt Models**
    -   **Action:** Run `dbt build` to materialize the new and updated models.
    -   **Command:**
        ```bash
        cd eras_dbt && dbt build --profiles-dir .
        ```

### Phase 2: Dashboard Update

6.  **Update Data Repository**
    -   **File:** `D:/ErasProjects/ErasOpera/dashboard/data/repository.py`
    -   **Action:** Modify `fetch_kpi_daily_segmented` to accept new segment columns (`market_segment_name`, `source_channel_name`, `room_type_name`).
    -   **Note:** The function is already dynamic, so we just need to ensure the calling code in `segments.py` passes the new column names. No direct change to the SQL generation is needed, but we must verify it handles the new columns correctly.

7.  **Update Segments Tab**
    -   **File:** `D:/ErasProjects/ErasOpera/dashboard/ui/tabs/segments.py`
    -   **Action:**
        -   Change the `fetch_kpi_daily_segmented` calls to use the new `*_name` columns instead of `*_code` columns.
        -   Update the `alt.X` and `alt.Y` encodings in the Altair charts to use the new columns (`market_segment_name`, `source_channel_name`, `room_type_name`).
        -   Update the axis titles and tooltips to be more descriptive (e.g., `t("axis.market_segment")`).
        -   Remove the entire `col3` block that contains the "Roomnights by Rate Plan" chart.

## 8. Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| dbt models build successfully | Fully-Automated | `dbt build --profiles-dir .` exits 0. |
| New dimension tables exist in the warehouse | Hybrid | Connect to Postgres and run `SELECT * FROM analytics.dim_market LIMIT 1;` etc. |
| Dashboard Segments tab loads without error | Agent-Probe | Start the dashboard and navigate to the "Phân khúc" tab. |
| Charts use business-friendly names | Agent-Probe | Visually inspect the chart axes and tooltips on the Segments tab to confirm names like "Corporate" are used, not "CORP". |
| "By Rate Plan" chart is gone | Agent-Probe | Visually inspect the Segments tab to confirm only three charts are present. |

## 9. Test Infra Improvement Notes

(none identified yet)

## 10. Resume and Execution Handoff

- **Selected Plan File Path:** `D:/ErasProjects/ErasOpera/process/general-plans/active/dashboard-v2-segment-refactor_22-07-26/dashboard-v2-segment-refactor_PLAN_22-07-26.md`
- **Last Completed Phase:** PLAN
- **Validate Contract Status:** Pending. `vc-validate-agent` must be run before EXECUTE.
- **Supporting Context Files Loaded:**
    - `D:/ErasProjects/ErasOpera/process/context/all-context.md`
    - `D:/ErasProjects/ErasOpera/process/context/database/all-database.md`
    - `D:/ErasProjects/ErasOpera/dashboard/app.py`
    - `D:/ErasProjects/ErasOpera/dashboard/ui/tabs/segments.py`
    - `D:/ErasProjects/ErasOpera/dashboard/data/repository.py`
- **Next Step:** Run `vc-validate-agent` on this plan file to generate the validate contract.

## 11. Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)
