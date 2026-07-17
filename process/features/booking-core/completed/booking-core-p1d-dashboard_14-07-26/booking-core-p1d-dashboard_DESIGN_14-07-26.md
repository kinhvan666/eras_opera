# Design: Booking Core - Phase 1d V1 Leadership Dashboard

**Date:** 14-07-26
**Feature:** booking-core
**Phase:** 1d (Dashboard V1)
**Status:** DRAFT - Pending Review

---

## 1. Executive Summary

V1 Leadership Dashboard cho booking-core feature. Visualize 8 KPIs từ SPEC trên dữ liệu dimensional layer đã hoàn thành (Phase 3). Single-page Streamlit app, deployed as Docker container, reads from PostgreSQL via dbt-computed KPI tables.

**Scope:** 8 KPIs, 3 tabs (Trends, Segments, Pacing), explicit "Estimated" badges, date/property/rate filters.

---

## 2. Visual Design Specification

### 2.1 Color System (Modern Data-Dense Style)

| Token | Light Mode | Dark Mode | Usage |
|---|---|---|---|
| `--bg-primary` | `#F8F9FA` | `#1A1A1A` | Page background |
| `--bg-card` | `#FFFFFF` | `#2C2C2C` | Card/Widget background |
| `--text-primary` | `#212529` | `#E9ECEF` | Primary text, KPI values |
| `--text-secondary`| `#6C757D` | `#ADB5BD` | Labels, secondary info |
| `--accent-blue` | `#0D6EFD` | `#4D94FF` | Primary actions, links, highlights |
| `--kpi-positive` | `#198754` | `#34C759` | Positive trends/metrics |
| `--kpi-negative` | `#DC3545` | `#FF453A` | Negative trends/metrics |
| `--kpi-neutral` | `#6C757D` | `#8E8E93` | Neutral metrics, context info |
| `--badge-estimated`| `#FFC107` | `#FFD60A` | "Estimated" badge background |
| `--border` | `#DEE2E6` | `#495057` | Card borders, dividers |
| `--grid-gap` | `16px` | `16px` | Grid gap |
| `--card-padding` | `16px` | `16px` | Card internal padding |

### 2.2 Typography (Modern Sans-Serif)

```css
/* Google Fonts Import */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --font-sans: 'Inter', sans-serif;
}

/* Scale */
--text-xs: 12px/1.5 var(--font-sans);    /* Filters, axis labels, badges */
--body: 14px/1.6 var(--font-sans);          /* General text */
--h4: 16px/1.5 var(--font-sans);            /* KPI labels, card titles */
--h3: 20px/1.4 var(--font-sans);            /* Section headers */
--h2: 24px/1.3 var(--font-sans);            /* Page Title */
--kpi-value: 32px/1.2 var(--font-sans);     /* KPI metric values */
```

### 2.3 Layout Grid (Data-Dense Dashboard)

- **Grid:** 12-column CSS Grid, gap: 8px
- **Header:** 56px height, sticky
- **KPI Row:** 6-8 cards, responsive wrap
- **Tabs:** Full-width, 48px tab bar
- **Chart Cards:** Min-width 280px, flex-grow

---

## 3. Information Architecture

### 3.1 Single Page Layout

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ErasOpera > Booking Core Dashboard                                               [Date Filter]    │
│ Project: ErasOpera                                                                                │
├─────────────────────────────────────────────────────────────────────────────────┬─────────────────┤
│ Booking Analytics (KPI Row)                                                     │ Pacing Overview │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐         │ ┌───────────────┤
│ │ Occupancy │ │    ADR    │ │  RevPAR   │ │  Revenue  │ │Reservations │         │ │ Pacing vs LY  │
│ │   72.3%   │ │  $1,250   │ │  $903     │ │  $1.2M    │ │    1,247    │         │ │ (Line + Band) │
│ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘         │ │               │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐                                     │ └───────────────┤
│ │Room Nights│ │ Lead Time │ │Canc. Rate │                                     │                 │
│ │   2,847   │ │   23.4d   │ │   14.2%   │                                     │ Pickup Analysis │
│ └───────────┘ └───────────┘ └───────────┘                                     │ ┌───────────────┤
│                                                                                 │ │ Last 7/30/90d │
├───────────────────────────────────────────────────────────────────────────────┤ │ (Table+Spark) │
│ Trend Analysis                                                                  │ └───────────────┤
│ ┌──────────────────────────┐ ┌──────────────────────────┐ ┌────────────────────┤                 │
│ │ Occupancy Trend          │ │ ADR / RevPAR Trend       │ │ Bookings Pace      │ Segment Analysis│
│ │ (Line + Area)            │ │ (Dual-axis Line)         │ │ (Cumulative Line)  │ ┌───────────────┤
│ └──────────────────────────┘ └──────────────────────────┘ └────────────────────┘ │ By Market     │
│                                                                                 │ (Stacked Bar) │
├─────────────────────────────────────────────────────────────────────────────────┤                 │
│ Segment Analysis (continued)                                                    │ By Source     │
│ ┌──────────────────────────┐ ┌──────────────────────────┐ ┌────────────────────┤ (Horiz. Bar)  │
│ │ By Rate Plan             │ │ By Room Type             │ │ Cancellation Trend │ └───────────────┤
│ │ (Grouped Bar)            │ │ (Bullet Chart)           │ │ (Bar + Line)       │                 │
│ └──────────────────────────┘ └──────────────────────────┘ └────────────────────┘                 │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. KPI Definitions & Computation

### 4.1 KPI Table (from SPEC + Data Reality)

| # | KPI | Label | Formula (SQL) | Status | Badge |
|---|-----|-------|---------------|--------|-------|
| 1 | Occupancy (est.) | Occupancy | `COUNT(*) / (room_count * date_range_days)` | Partial* | EST |
| 2 | ADR (est.) | ADR | `SUM(night_amount) / COUNT(*)` | Ready | EST |
| 3 | RevPAR (est.) | RevPAR | `SUM(night_amount) / (room_count * date_range_days)` | Partial* | EST |
| 4 | Total Revenue (est.) | Revenue | `SUM(night_amount)` | Ready | EST |
| 5 | Reservations | Reservations | `COUNT(DISTINCT reservation_id)` | Ready | — |
| 6 | Room Nights | Room Nights | `COUNT(*)` | Ready | — |
| 7 | Avg Lead Time | Lead Time | `AVG(arrival_date - booking_date)` | Partial** | — |
| 8 | Cancellation Rate | Canc. Rate | `COUNT(*) FILTER (WHERE status='Cancelled') / COUNT(*)` | Partial** | — |

*Partial: Needs `room_count` in `dim_property` (manual entry for V1)
**Partial: Needs `booking_date` (from `created_at`) and `reservation_status` in `fct_reservation_night`

### 4.2 dbt KPI Models (New Files)

```
eras_dbt/models/marts/
├── kpi_daily_snapshot.sql       -- Daily grain KPIs per property
├── kpi_pacing.sql               -- Pacing vs prior year
├── kpi_pickup.sql               -- 7/30/90 day pickup
└── schema.yml                   -- Tests: not_null, accepted_values
```

**KPI Model Pattern:**
```sql
-- kpi_daily_snapshot.sql
with daily as (
  select
    f.business_date,
    f.hotel_id,
    count(distinct f.reservation_id) as reservations,
    count(*) as room_nights,
    sum(f.night_amount) as total_revenue,
    sum(f.night_amount) / nullif(count(*), 0) as adr,
    -- room_count from dim_property (manual for V1)
    p.room_count
  from {{ ref('fct_reservation_night') }} f
  join {{ ref('dim_property') }} p on f.hotel_id = p.hotel_id
  group by 1, 2, p.room_count
)
select
  *,
  room_nights / nullif(room_count * 1.0, 0) as occupancy,
  total_revenue / nullif(room_count * 1.0, 0) as revpar
from daily
```

---

## 5. Data Requirements (dbt Changes)

### 5.1 Fact Table Extension (fct_reservation_night)

```sql
-- Add to fct_reservation_night.sql
select
  ...,
  s.created_at::date as booking_date,
  s.reservation_status  -- 'Confirmed', 'Cancelled', 'CheckedOut', 'NoShow'
from stg_reservations s
```

**Migration:** Update `fct_reservation_night` + run `dbt run --full-refresh`

### 5.2 Dimension Property Extension (dim_property)

```sql
-- dim_property.sql
select
  hotel_id,
  hotel_name,
  250 as room_count  -- MANUAL ENTRY for V1 (single property)
```

### 5.3 Estimated Badge Logic

All financial KPIs (ADR, RevPAR, Revenue, Occupancy) → UI badge "EST" (Amber #F59E0B)

---

## 6. Dashboard Implementation (Streamlit)

### 6.1 Project Structure

```
dashboard/
├── Dockerfile
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── app.py                    # Entry point
├── config/
│   └── settings.py           # DB conn, cache TTL
├── data/
│   ├── repository.py         # SQL queries, caching
│   └── kpi.py                # KPI computation helpers
├── ui/
│   ├── components.py         # KPICard, ChartWrapper, FilterBar
│   ├── tabs/
│   │   ├── trends.py
│   │   ├── segments.py
│   │   └── pacing.py
│   └── layout.py             # Page structure
└── styles/
    └── theme.css             # Custom CSS injection
```

### 6.2 Key Components

**KPICard:**
```python
def kpi_card(label: str, value: str, delta: str = None, badge: str = None):
    """Renders a metric card with optional trend delta and EST badge."""
```

**FilterBar:**
```python
def filter_bar():
    """Property, Market, Rate Plan, Date Range - pushes to URL query params."""
```

**ChartWrapper:**
```python
def chart_wrapper(title: str, fig, height: int = 350):
    """Consistent card container for all charts."""
```

### 6.3 Caching Strategy

```python
@st.cache_data(ttl=300)  # 5 min TTL
def fetch_kpi_daily(start_date, end_date, hotel_id):
    return pd.read_sql(KPI_DAILY_SQL, conn, params=...)
```

---

## 7. Deployment (Docker)

### 7.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 7.2 docker-compose.yml (add to root)

```yaml
services:
  dashboard:
    build: ./dashboard
    container_name: erasopera_dashboard
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/erg_opera_data
    depends_on:
      - db
    volumes:
      - ./dashboard:/app  # dev hot-reload
```

---

## 8. Test & Verification

| Test | Method | Criteria |
|------|--------|----------|
| KPI SQL correctness | `dbt test --select kpi_*` | All tests pass |
| Dashboard loads | Manual / Playwright | No 500 errors, KPIs render |
| Filter interactions | Playwright | Date/Property filters update charts |
| Estimate badges visible | Visual | All financial KPIs show [EST] |
| Responsive layout | Browser devtools | Works at 1280px, 1920px, 375px |
| Data freshness | Manual | Cache TTL respected, new data appears within 5 min |

---

## 9. Open Questions / Decisions Needed

1. **Room count for V1:** Hardcode `250` in `dim_property` or env var?
2. **Date range default:** Last 30 days? Last 90 days? Configurable?
3. **Pacing comparison:** Compare to same period last year? Or fixed baseline?
4. **Export:** CSV export button for KPI table? (Nice to have)
5. **Multi-property:** `dim_property` has 1 row now. Design supports N, but UI defaults to first.

---

## 10. Implementation Checklist (for PLAN)

### Phase A: dbt KPI Layer
- [ ] Add `booking_date`, `reservation_status` to `fct_reservation_night`
- [ ] Add `room_count` to `dim_property`
- [ ] Create `kpi_daily_snapshot`, `kpi_pacing`, `kpi_pickup` models
- [ ] Add dbt tests (not_null, accepted_values)
- [ ] `dbt run --full-refresh` + `dbt test`

### Phase B: Dashboard Skeleton
- [ ] Create `dashboard/` folder structure
- [ ] Dockerfile, requirements.txt, .streamlit/config.toml
- [ ] `app.py` with page config, header, filter bar
- [ ] Theme CSS injection (Fira fonts, color tokens)

### Phase C: KPI Row & Data Layer
- [ ] `data/repository.py` with cached query functions
- [ ] `ui/components.py` - KPICard, FilterBar
- [ ] Wire KPI row to `kpi_daily_snapshot` table

### Phase D: Tabs Implementation
- [ ] Trends tab (4 charts)
- [ ] Segments tab (4 charts)
- [ ] Pacing tab (2 charts)

### Phase E: Polish & Deploy
- [ ] Estimate badges on financial KPIs
- [ ] Responsive testing
- [ ] Add to docker-compose.yml
- [ ] Documentation (README.md)

---

## 11. Reviewer Checklist

- [ ] Visual design matches "Data-Dense Dashboard" style
- [ ] All 8 SPEC KPIs addressed (6 ready, 2 partial, 2 blocked on other features)
- [ ] "Estimated" badges on financial KPIs per SPEC requirement
- [ ] Single-page layout with KPI row + tabs matches SPEC "single dashboard"
- [ ] Streamlit + Docker deployment is simplest viable option
- [ ] dbt KPI layer keeps business logic testable and reusable
- [ ] Missing data (room_count, booking_date, status) has clear V1 workaround

---

**Next Step:** Approve design → Run `vc-generate-plan` to create Phase 1d plan artifact.