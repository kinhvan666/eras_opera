# Design Document: Booking Core - Phase 1d V1 Leadership Dashboard

**Date:** 14-07-26
**Feature:** booking-core
**Phase:** 1d (Dashboard V1)
**Status:** DRAFT - Pending Review
**SPEC Reference:** `process/features/booking-core/active/booking-core_SPEC_13-07-26.md`
**Completed Phases:** Phase 1a (Extractor), Phase 1b (Staging), Phase 1c (Dimensional Model)

---

## 1. Executive Summary

V1 Leadership Dashboard cho booking-core feature. Visualize 8 KPIs từ SPEC trên dữ liệu dimensional layer đã hoàn thành (Phase 3). Single-page Streamlit app, deployed as Docker container, reads từ PostgreSQL via dbt-computed KPI tables.

**Scope:** 8 KPIs, 3 tabs (Trends, Segments, Pacing), explicit "Estimated" badges, date/property/rate filters.

---

## 2. INNOVATE Decisions Recap

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **1. Framework** | **Streamlit** | Fastest prototype, native widgets, 100% Python |
| **2. Deployment** | **Docker container** | Portable, no external deps, version-controlled |
| **3. KPI Computation** | **dbt materialized views** | Logic in transformation layer, testable, reusable |
| **4. Data Freshness** | **Live queries + 5-min cache** | Tiny data (118 rows), always current, zero infra |
| **5. Auth** | **None (internal/VPN)** | V1 = internal prototype; add auth when real need |
| **6. Missing KPIs** | **Denormalize fact table** | Add `booking_date` + `reservation_status` to `fct_reservation_night`; `room_count` to `dim_property` |
| **7. Structure** | **Single page: KPI row + tabs** | Matches SPEC "single dashboard" + 6 business questions |

---

## 3. Visual Design Specification

### 3.1 Color System (Data-Dense Dashboard Style)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--bg-primary` | `#F5F5F5` | `#1E1E1E` | Page background |
| `--bg-card` | `#FFFFFF` | `#2D2D2D` | Card/KPI background |
| `--text-primary` | `#333333` | `#EAEAEA` | Primary text |
| `--text-secondary` | `#666666` | `#AAAAAA` | Labels, secondary info |
| `--accent-blue` | `#1976D2` | `#64B5F6` | Primary actions, links |
| `--kpi-profit` | `#22C55E` | `#4ADE80` | Positive metrics (ADR, RevPAR) |
| `--kpi-loss` | `#EF4444` | `#F87171` | Negative metrics (Cancellation) |
| `--kpi-neutral` | `#1976D2` | `#64B5F6` | Neutral metrics (Occupancy, Lead Time) |
| `--badge-estimated` | `#F59E0B` | `#FBBF24` | "Estimated" badge background |
| `--border` | `#E0E0E0` | `#444444` | Card borders, dividers |
| `--grid-gap` | `8px` | `8px` | Grid gap |
| `--card-padding` | `12px` | `12px` | Card internal padding |

### 3.2 Typography (Fira Family - Dashboard Data)

```css
/* Google Fonts Import */
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --font-mono: 'Fira Code', monospace;      /* KPI values, data labels */
  --font-sans: 'Fira Sans', sans-serif;     /* Labels, UI text, headings */
}

/* Scale */
--text-xs: 11px/1.4 var(--font-sans);    /* Filters, axis labels, badges */
--body: 14px/1.5 var(--font-sans);       /* General text */
--h4: 16px/1.4 var(--font-sans);         /* KPI labels, card titles */
--h3: 20px/1.3 var(--font-sans);         /* Section headers */
--h2: 28px/1.2 var(--font-sans);         /* Tab headers */
--kpi-value: 36px/1.1 var(--font-mono);  /* KPI values */
```

### 3.3 Spacing & Layout

| Token | Value | Usage |
|-------|-------|-------|
| `--grid-gap` | 8px | Grid gap |
| `--card-padding` | 12px | Card internal padding |
| `--sidebar-width` | 240px | Filter sidebar (if needed) |
| `--header-height` | 56px | Top filter bar |
| `--kpi-row-height` | auto | KPI card row |
| `--chart-height` | 300px | Standard chart height |

---

## 4. Layout Architecture

### 4.1 Page Structure (Single Page)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ HEADER BAR (56px)                                                        │
│ [ErasOpera Logo]  Booking Core V1 Dashboard          [Date Range] [Property ▼] │
├─────────────────────────────────────────────────────────────────────────┤
│ KPI ROW (8 cards, responsive grid)                                       │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │Total Rev│ │   ADR   │ │RevPAR   │ │Occupancy│ │Reservat.│ │Room Nig.│ │Lead Time│ │Canc. Rate│ │
│ │(est.) ★ │ │(est.) ★ │ │(est.) ★ │ │(est.) ★ │ │         │ │         │ │         │ │         │ │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ TABS                                                                     │
│ [ Trends ] [ Segments ] [ Pacing ]                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ TAB CONTENT AREA                                                         │
│ (Scrollable)                                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Responsive Grid

```css
/* KPI Row: 8 cards, responsive */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  padding: 12px;
}

/* Tab content: 2-column for charts, 1-col for tables */
.tab-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 8px;
  padding: 12px;
}
```

---

## 5. KPI Card Design

### 5.1 Card Structure

```
┌─────────────────────────────────────┐
│  KPI Label (16px, Fira Sans, #666)  │
│  ─────────────────────────────────  │
│  1,234,567,890  (36px, Fira Code)   │
│  ┌──────────┐                       │
│  │ESTIMATED │  (11px, badge, amber) │
│  └──────────┘                       │
└─────────────────────────────────────┘
```

### 5.2 KPI Cards Specification

| # | KPI | Label | Value Format | Badge | Color | Data Source |
|---|-----|-------|--------------|-------|-------|-------------|
| 1 | Total Revenue (est.) | Total Revenue | `1,234,567,890 VND` | ★ ESTIMATED | profit | `kpi_total_revenue` |
| 2 | ADR (est.) | Avg Daily Rate | `2,345,678 VND` | ★ ESTIMATED | profit | `kpi_adr` |
| 3 | RevPAR (est.) | RevPAR | `1,778,989 VND` | ★ ESTIMATED | profit | `kpi_revpar` |
| 4 | Occupancy (est.) | Occupancy | `75.8%` | ★ ESTIMATED | neutral | `kpi_occupancy` |
| 5 | Total Reservations | Reservations | `100` | — | neutral | `kpi_reservations` |
| 6 | Total Room Nights | Room Nights | `118` | — | neutral | `kpi_room_nights` |
| 7 | Avg Lead Time | Avg Lead Time | `21.5 days` | — | neutral | `kpi_lead_time` |
| 8 | Cancellation Rate | Cancellation Rate | `8.5%` | — | loss | `kpi_cancellation_rate` |

**Badge Rules:**
- Financial KPIs (Revenue, ADR, RevPAR, Occupancy) → `ESTIMATED` badge (amber)
- Operational KPIs (Reservations, Room Nights, Lead Time, Cancellation) → No badge (actual from data)

---

## 6. Tab Specifications

### 6.1 Tab 1: Trends (Time-Series Analysis)

**Purpose:** Answer "How is booking activity trending?" and "How much are guests paying on average?"

| Chart | Type | X-Axis | Y-Axis | Series | Library |
|-------|------|--------|--------|--------|---------|
| Room Nights & Revenue | Dual-axis: Bar + Line | Date (daily) | Room Nights (bar, left) / Revenue (line, right) | Room Nights, Total Revenue | Plotly/Altair |
| ADR & RevPAR Trend | Line | Date (daily) | VND | ADR, RevPAR | Plotly/Altair |
| Avg Lead Time | Line | Date (daily) | Days | Lead Time | Plotly/Altair |
| Cancellation Rate | Line | Date (daily) | % | Cancellation Rate | Plotly/Altair |

**Interactions:**
- Hover tooltip: exact values
- Date range filter (from header) applies to all
- Legend click: toggle series

### 6.2 Tab 2: Segments (Dimensional Slicing)

**Purpose:** Answer "How effective are we at filling the hotel at a good rate?" and "Which segments drive performance?"

| Chart | Type | Dimensions | Metrics | Library |
|-------|------|------------|---------|---------|
| Revenue by Market Code | Horizontal Bar | `market_code` | Revenue, Room Nights, ADR | Plotly/Altair |
| Revenue by Rate Plan | Horizontal Bar | `rate_plan_code` | Revenue, Room Nights, ADR | Plotly/Altair |
| Revenue by Source of Business | Horizontal Bar | `source_of_business` | Revenue, Room Nights | Plotly/Altair |
| Room Nights by Room Type | Stacked Bar | `room_type` | Room Nights (by status) | Plotly/Altair |
| Reservations by Country | Table | `guest_country_code` | Reservations, Room Nights, Avg Revenue | Streamlit `st.dataframe` |

**Interactions:**
- Click bar → filter other charts (cross-filter)
- Sort: by Revenue (default) or Room Nights

### 6.3 Tab 3: Pacing (Booking Pace Analysis)

**Purpose:** Answer "How far in advance are guests booking?" and "How many bookings are being cancelled?"

| Chart | Type | Description |
|-------|------|-------------|
| Booking Pace Curve | Line | X: Days Before Arrival (0-90), Y: Cumulative Reservations. Multiple lines: current year vs prior year vs target. |
| Pickup by Week | Bar | Weekly new bookings vs cancellations. Stacked: new (green) / cancelled (red). |
| Lead Time Distribution | Histogram | Distribution of `arrival_date - booking_date` for reservations in selected period. |
| Cancellation Funnel | Funnel | Total → Active → Cancelled → No-show (if data available) |

---

## 7. Data Architecture

### 7.1 New dbt KPI Models (Materialized Views)

```yaml
# eras_dbt/models/kpi/
kpi_total_revenue.sql      -- SUM(night_amount) from fct_reservation_night
kpi_adr.sql                -- SUM(night_amount) / COUNT(*) 
kpi_revpar.sql             -- SUM(night_amount) / (room_count * date_count)
kpi_occupancy.sql          -- COUNT(*) / (room_count * date_count)
kpi_reservations.sql       -- COUNT(DISTINCT reservation_id)
kpi_room_nights.sql        -- COUNT(*)
kpi_lead_time.sql          -- AVG(booking_date - arrival_date) [needs booking_date in fact]
kpi_cancellation_rate.sql  -- COUNT(WHERE status='Cancelled') / COUNT(*) [needs status in fact]
```

### 7.2 Fact Table Extensions (Denormalization)

**File:** `eras_dbt/models/dimensional/fct_reservation_night.sql`

**Add columns:**
```sql
-- Booking date (reservation grain, repeated per night)
raw_data->>'createDateTime' as booking_date,

-- Reservation status (repeated per night)
raw_data->>'reservationStatus' as reservation_status,
```

**Update grain declaration:** Still `property_id, reservation_id, business_date` (night grain)

### 7.3 Dimension Extensions

**File:** `eras_dbt/models/dimensional/dim_property.sql`
```sql
-- Add room_count (nullable, manual entry for V1)
NULL as room_count
```

---

## 8. Technical Implementation

### 8.1 Project Structure

```
eras_dashboard/
├── Dockerfile
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── dashboard/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # DB connection, constants
│   ├── data/
│   │   ├── __init__.py
│   │   ├── queries.py          # SQL queries for KPIs/charts
│   │   └── loader.py           # Cached data loading functions
│   ├── components/
│   │   ├── __init__.py
│   │   ├── kpi_card.py         # KPI card component
│   │   ├── charts.py           # Chart components
│   │   └── filters.py          # Filter components
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── trends.py           # Trends tab
│   │   ├── segments.py         # Segments tab
│   │   └── pacing.py           # Pacing tab
│   └── styles/
│       └── theme.py            # Streamlit theme config
└── tests/
    ├── __init__.py
    ├── test_queries.py
    └── test_components.py
```

### 8.2 Key Dependencies (`requirements.txt`)

```text
streamlit>=1.35.0
pandas>=2.0.0
plotly>=5.18.0
altair>=5.2.0
psycopg2-binary>=2.9.0
python-dotenv>=1.0.0
pytest>=7.4.0
```

### 8.3 Caching Strategy

```python
# In data/loader.py
@st.cache_data(ttl=300)  # 5-minute cache
def load_kpi_data(query: str, params: tuple) -> pd.DataFrame:
    """Execute query and return DataFrame with 5-min cache."""
    ...

@st.cache_data(ttl=300)
def load_chart_data(query: str, params: tuple) -> pd.DataFrame:
    """Execute query for chart data."""
    ...
```

### 8.4 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard/ ./dashboard/
COPY .streamlit/ ./.streamlit/

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "dashboard/main.py"]
```

### 8.4 Docker Compose (Add to existing)

```yaml
# Add to existing docker-compose.yml
services:
  dashboard:
    build: ./eras_dashboard
    container_name: eras_dashboard
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/erg_opera_data
    depends_on:
      - db
    restart: unless-stopped
```

---

## 9. Acceptance Criteria (from SPEC + Design)

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Dashboard loads in < 3s | Manual test |
| 2 | All 8 KPI cards display correct values matching dbt models | Compare dashboard vs `SELECT * FROM kpi_*` |
| 3 | Financial KPIs show "ESTIMATED" badge | Visual inspection |
| 4 | Date range filter updates all charts | Interaction test |
| 5 | Property filter updates all data | Interaction test |
| 6 | Trends tab: 4 time-series charts render correctly | Visual + data spot-check |
| 7 | Segments tab: 4 segment charts + 1 table render | Visual + data spot-check |
| 8 | Pacing tab: 4 pacing charts render | Visual + data spot-check |
| 9 | Docker container builds and runs locally | `docker-compose up dashboard` |
| 10 | No hardcoded credentials; uses env vars | Code review |

---

## 10. Known Gaps & Future Work

| Gap | Priority | Resolution |
|-----|----------|------------|
| Room count for Occupancy/RevPAR denominator | High | Manual `room_count` in `dim_property` for V1; automate via Operations feature |
| Actual financial data (folio) | Medium | Phase 2: Financials feature integration |
| Auth/Authorization | Low | Add when multi-user need arises |
| Real-time refresh / WebSocket | Low | Current 5-min cache sufficient for batch |
| Export (PDF/Excel) | Low | Add in V2 |
| Mobile responsive | Low | Desktop-first for V1 |

---

## 11. Review Checklist

- [ ] **Visual Design:** Colors, typography, spacing approved?
- [ ] **Layout:** Single-page KPI row + 3 tabs structure approved?
- [ ] **KPI Cards:** 8 cards, formats, badges correct?
- [ ] **Tabs:** Trends / Segments / Pacing charts comprehensive?
- [ ] **Data Architecture:** dbt KPI models + fact extensions feasible?
- [ ] **Tech Stack:** Streamlit + Docker + Plotly/Altair approved?
- [ ] **Deployment:** Docker Compose integration with existing stack?
- [ ] **Gaps:** Known limitations accepted for V1?

---

**Next Step:** Upon approval, proceed to **PLAN** phase to create implementation checklist and task breakdown.