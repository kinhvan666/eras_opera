from datetime import timedelta

import pandas as pd
import psycopg2
import streamlit as st

from config.settings import CACHE_TTL_SECONDS, DATABASE_URL

KPI_DAILY_SQL = """
    select business_date, hotel_id, reservations, room_nights, total_revenue,
           adr, occupancy, revpar, avg_lead_time, cancellation_rate
    from analytics.kpi_daily_snapshot
    where business_date between %(start_date)s and %(end_date)s
      and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
"""

KPI_DAILY_SEGMENTED_SQL = """
    select f.business_date, f.hotel_id, f.reservations, f.room_nights, f.total_revenue,
           f.adr, f.occupancy, f.revpar, f.avg_lead_time, f.cancellation_rate,
           s.market_code, s.source_of_business, s.rate_plan_code, s.room_type
    from analytics.kpi_daily_snapshot f
    join analytics.fct_reservation_night s
      on f.hotel_id = s.hotel_id and f.business_date = s.business_date
    where f.business_date between %(start_date)s and %(end_date)s
      and (%(hotel_id)s::text is null or f.hotel_id = %(hotel_id)s)
"""


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_properties():
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(
            "select hotel_id, hotel_name from analytics.dim_property order by hotel_id", conn
        )


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_kpi_daily(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(
            KPI_DAILY_SQL, conn, params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )


def _aggregate(df):
    if df.empty:
        return None
    return {
        "occupancy": df["occupancy"].mean(),
        "adr": df["adr"].mean(),
        "revpar": df["revpar"].mean(),
        "total_revenue": df["total_revenue"].sum(),
        "reservations": df["reservations"].sum(),
        "room_nights": df["room_nights"].sum(),
        "avg_lead_time": df["avg_lead_time"].mean(),
        "cancellation_rate": df["cancellation_rate"].mean(),
    }


def _prior_range(start_date, end_date):
    """Kỳ trước = khoảng liền trước có cùng độ dài, KHÔNG chồng lấn kỳ hiện tại.
    Ví dụ: 01/01–22/07 (203 ngày) → kỳ trước 12/06/25–31/12/25."""
    range_days = (end_date - start_date).days + 1
    prior_end = start_date - timedelta(days=1)
    prior_start = prior_end - timedelta(days=range_days - 1)
    return prior_start, prior_end


def fetch_kpi_summary(start_date, end_date, hotel_id=None):
    """Current vs prior-period aggregates for delta cards.
    Prior period = non-overlapping preceding window of equal length;
    returns None for prior when that window has no data (delta badge hidden)."""
    current = fetch_kpi_daily(start_date, end_date, hotel_id)
    prior_start, prior_end = _prior_range(start_date, end_date)
    prior = fetch_kpi_daily(prior_start, prior_end, hotel_id)
    return _aggregate(current), _aggregate(prior)


REVENUE_BREAKDOWN_SQL = """
    -- Join fct_folio_line (actual posted revenue) với fct_reservation_night
    -- để lấy market_code, rate_plan_code, room_type.
    -- Join chỉ theo reservation_id — không join theo date vì posting date
    -- (revenue_date) thường khác business_date (stay night).
    -- Dùng DISTINCT ON reservation để lấy attributes một lần, tránh fan-out.
    -- Fallback: nếu không có trong fct_reservation_night, lấy từ raw booking data.
    with folio as (
        select
            reservation_id,
            sum(posted_amount) as revenue
        from analytics.fct_folio_line
        where revenue_date between %(start_date)s and %(end_date)s
          and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
          and revenue_category != 'Tax'
        group by reservation_id
    ),
    res_attrs as (
        -- Lấy attributes từ fct_reservation_night (guest stays)
        select distinct on (reservation_id)
            reservation_id,
            market_code,
            rate_plan_code,
            room_type,
            reservation_status
        from analytics.fct_reservation_night
        where (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
        order by reservation_id, business_date
    ),
    raw_attrs as (
        -- Fallback: lấy từ raw booking data cho reservations không có trong fct_reservation_night
        select
            raw_data->'reservationIdList'->0->>'id'   as reservation_id,
            raw_data->'roomStay'->>'marketCode'       as market_code,
            raw_data->'roomStay'->>'ratePlanCode'     as rate_plan_code,
            raw_data->'roomStay'->>'roomType'         as room_type,
            raw_data->>'reservationStatus'            as reservation_status
        from raw.booking_core_reservations
    )
    select
        coalesce(r.market_code, rb.market_code, 'Unknown')    as market_code,
        coalesce(r.rate_plan_code, rb.rate_plan_code, 'Unknown') as rate_plan_code,
        coalesce(r.room_type, rb.room_type, 'Unknown')        as room_type,
        sum(f.revenue)                                        as revenue,
        count(*)                                              as transactions
    from folio f
    left join res_attrs r  on f.reservation_id = r.reservation_id
    left join raw_attrs rb on f.reservation_id = rb.reservation_id
                          and r.reservation_id is null  -- chỉ dùng fallback khi không có trong fct_reservation_night
    where coalesce(r.reservation_status, rb.reservation_status, '') not in ('Cancelled', 'NoShow')
    group by
        coalesce(r.market_code, rb.market_code, 'Unknown'),
        coalesce(r.rate_plan_code, rb.rate_plan_code, 'Unknown'),
        coalesce(r.room_type, rb.room_type, 'Unknown')
"""


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_revenue_breakdown(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(REVENUE_BREAKDOWN_SQL, conn,
                           params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id})


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_kpi_daily_segmented(start_date, end_date, hotel_id=None, segment_col=None):
    """Room nights and revenue per segment, queried directly from fct_reservation_night.

    Each row in fct_reservation_night = 1 room night, so count(*) = room nights.
    The old approach joined kpi_daily_snapshot (daily totals) × fact rows, causing
    fan-out multiplication (daily total counted once per reservation row).
    """
    if not segment_col:
        return pd.DataFrame()
    sql = f"""
        select
            {segment_col},
            count(*)            as room_nights,
            sum(night_amount)   as total_revenue
        from analytics.fct_reservation_night
        where business_date between %(start_date)s and %(end_date)s
          and reservation_status not in ('Cancelled', 'NoShow')
          and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
          and {segment_col} is not null
        group by {segment_col}
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id})


REVENUE_ACTUAL_SQL = """
    SELECT revenue_date, revenue_category, SUM(posted_amount) AS posted_amount
    FROM analytics.fct_folio_line
    WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
    GROUP BY revenue_date, revenue_category
    ORDER BY revenue_date, revenue_category
"""


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_revenue_actual(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(
            REVENUE_ACTUAL_SQL, conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )


REVENUE_ACTUAL_KPI_SQL = """
    SELECT SUM(posted_amount) AS revenue
    FROM analytics.fct_folio_line
    WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
      AND revenue_category != 'Tax'
"""


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def _fetch_revenue_actual_scalar(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        df = pd.read_sql(
            REVENUE_ACTUAL_KPI_SQL, conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )
    return df["revenue"].iloc[0] if not df.empty else 0.0


def fetch_revenue_actual_summary(start_date, end_date, hotel_id=None):
    """Actual revenue KPI (excl. Tax) for current and prior period. Same prior-range logic as fetch_kpi_summary."""
    prior_start, prior_end = _prior_range(start_date, end_date)
    current_rev = _fetch_revenue_actual_scalar(start_date, end_date, hotel_id)
    prior_rev = _fetch_revenue_actual_scalar(prior_start, prior_end, hotel_id)
    return current_rev, prior_rev


ROOM_REVENUE_SQL = """
    SELECT COALESCE(SUM(posted_amount), 0) AS room_revenue
    FROM analytics.fct_folio_line
    WHERE revenue_date BETWEEN %(start_date)s AND %(end_date)s
      AND revenue_category = 'Room'
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""

ROOM_NIGHTS_SQL = """
    SELECT COUNT(*) AS room_nights
    FROM analytics.fct_reservation_night
    WHERE business_date BETWEEN %(start_date)s AND %(end_date)s
      AND reservation_status NOT IN ('Cancelled', 'NoShow')
      AND (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""

ROOM_COUNT_SQL = """
    SELECT COALESCE(MAX(room_count), 0) AS room_count
    FROM analytics.dim_property
    WHERE (%(hotel_id)s::text IS NULL OR hotel_id = %(hotel_id)s)
"""


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def _fetch_adr_revpar_inputs(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        room_rev = pd.read_sql(ROOM_REVENUE_SQL, conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )["room_revenue"].iloc[0]
        room_nights = pd.read_sql(ROOM_NIGHTS_SQL, conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id}
        )["room_nights"].iloc[0]
        room_count = pd.read_sql(ROOM_COUNT_SQL, conn,
            params={"hotel_id": hotel_id}
        )["room_count"].iloc[0]
    days = (end_date - start_date).days + 1
    adr = float(room_rev) / room_nights if room_nights > 0 else None
    revpar = float(room_rev) / (room_count * days) if room_count > 0 else None
    return adr, revpar


def fetch_adr_revpar_actual_summary(start_date, end_date, hotel_id=None):
    """Actual ADR and RevPAR for current and prior period. Same prior-range logic as fetch_kpi_summary."""
    prior_start, prior_end = _prior_range(start_date, end_date)
    curr_adr, curr_revpar = _fetch_adr_revpar_inputs(start_date, end_date, hotel_id)
    prior_adr, prior_revpar = _fetch_adr_revpar_inputs(prior_start, prior_end, hotel_id)
    return curr_adr, curr_revpar, prior_adr, prior_revpar


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_kpi_pacing(start_date, end_date, hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(
            """
            select business_date, hotel_id, current_occupancy, prior_occupancy, occupancy_pace_pct,
                   current_adr, prior_adr, adr_pace_pct, current_revpar, prior_revpar, revpar_pace_pct,
                   current_revenue, prior_revenue, revenue_pace_pct, current_reservations, prior_reservations,
                   current_room_nights, prior_room_nights
            from analytics.kpi_pacing
            where business_date between %(start_date)s and %(end_date)s
              and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
            """,
            conn,
            params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id},
        )


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_kpi_pickup(hotel_id=None):
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(
            """
            select hotel_id, window_days, pickup_rooms, pickup_revenue
            from analytics.kpi_pickup
            where (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
            """,
            conn,
            params={"hotel_id": hotel_id},
        )


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_data_as_of():
    """Return the latest revenue_date in fct_folio_line as a date object."""
    with psycopg2.connect(DATABASE_URL) as conn:
        row = pd.read_sql(
            "SELECT MAX(revenue_date) AS as_of FROM analytics.fct_folio_line",
            conn,
        )
    val = row["as_of"].iloc[0]
    if pd.isna(val):
        return None
    return pd.Timestamp(val).date()
