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


def fetch_kpi_summary(start_date, end_date, hotel_id=None):
    """Current vs prior-period aggregates for delta cards.
    Per VALIDATE spec: WoW (shift 7d) for ranges <=14 days, MoM (shift 30d) for longer ranges."""
    current = fetch_kpi_daily(start_date, end_date, hotel_id)
    range_days = (end_date - start_date).days + 1
    shift = timedelta(days=7 if range_days <= 14 else 30)
    prior = fetch_kpi_daily(start_date - shift, end_date - shift, hotel_id)
    return _aggregate(current), _aggregate(prior)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_kpi_daily_segmented(start_date, end_date, hotel_id=None, segment_col=None):
    """Fetch daily KPI data joined with reservation-level segments for segmentation charts."""
    sql = KPI_DAILY_SEGMENTED_SQL
    if segment_col:
        sql += f" and s.{segment_col} is not null"
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(sql, conn, params={"start_date": start_date, "end_date": end_date, "hotel_id": hotel_id})


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
