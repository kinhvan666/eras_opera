from datetime import date, timedelta

import pandas as pd
import psycopg2
import streamlit as st

from config.settings import CACHE_TTL_SECONDS, DATABASE_URL

# 5 Executive KPIs
EXEC_KPI_SQL = """
    select business_date, hotel_id,
           sum(room_nights) as room_nights,
           sum(total_revenue) as total_revenue,
           sum(total_revenue) / nullif(sum(room_nights), 0) as adr,
           sum(room_nights) / nullif(sum(hotel_room_count) * 1.0, 0) as occupancy,
           sum(total_revenue) / nullif(sum(hotel_room_count) * 1.0, 0) as revpar,
           avg(cancellation_rate) as cancellation_rate
    from (
        select f.*, p.room_count as hotel_room_count
        from analytics.kpi_daily_snapshot f
        join analytics.dim_property p on f.hotel_id = p.hotel_id
    ) d
    where business_date between %(start_date)s and %(end_date)s
      and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
    group by business_date, hotel_id
"""

# Property portfolio query (for Properties tab)
PROPERTY_PORTFOLIO_SQL = """
    select f.hotel_id,
           p.hotel_name,
           sum(f.total_revenue) as total_revenue,
           sum(f.total_revenue) / nullif(sum(f.room_nights), 0) as adr,
           sum(f.room_nights) / nullif(sum(p.room_count) * 1.0, 0) as occupancy,
           sum(f.total_revenue) / nullif(sum(p.room_count) * 1.0, 0) as revpar,
           sum(case when f.cancellation_rate > 0.15 then 1 else 0 end)::int as risk_flag
    from analytics.kpi_daily_snapshot f
    join analytics.dim_property p on f.hotel_id = p.hotel_id
    where f.business_date between %(start_date)s and %(end_date)s
      and (%(hotel_id)s::text is null or f.hotel_id = %(hotel_id)s)
    group by f.hotel_id, p.hotel_name
"""

# Sparkline data per KPI per property
SPARKLINE_SQL = """
    select business_date, hotel_id,
           sum(total_revenue) as total_revenue,
           sum(total_revenue) / nullif(sum(room_nights), 0) as adr,
           sum(room_nights) / nullif(sum(hotel_room_count) * 1.0, 0) as occupancy,
           sum(total_revenue) / nullif(sum(hotel_room_count) * 1.0, 0) as revpar
    from (
        select f.*, p.room_count as hotel_room_count
        from analytics.kpi_daily_snapshot f
        join analytics.dim_property p on f.hotel_id = p.hotel_id
    ) d
    where business_date between %(start_date)s and %(end_date)s
      and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
    group by business_date, hotel_id
    order by business_date
"""

# Monthly revenue aggregation (for Overview bar chart)
MONTHLY_REVENUE_SQL = """
    select
        date_trunc('month', business_date)::date as month,
        sum(total_revenue)                        as monthly_revenue,
        sum(room_nights)                          as monthly_room_nights
    from analytics.kpi_daily_snapshot
    where business_date between %(start_date)s and %(end_date)s
      and (%(hotel_id)s::text is null or hotel_id = %(hotel_id)s)
    group by 1
    order by 1
"""


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_executive_properties():
    """Fetch all properties. Only queries columns that exist in dim_property."""
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql("""
            select hotel_id, hotel_name, room_count
            from analytics.dim_property
            order by hotel_id
        """, conn)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_executive_kpi_daily(start_date, end_date, hotel_id=None):
    """Fetch aggregated executive KPIs (5 metrics) for date range."""
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(EXEC_KPI_SQL, conn, params={
            "start_date": start_date, "end_date": end_date, "hotel_id": hotel_id
        })


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_property_portfolio(start_date, end_date, hotel_id=None):
    """Fetch property portfolio comparison for Properties tab."""
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(PROPERTY_PORTFOLIO_SQL, conn, params={
            "start_date": start_date, "end_date": end_date, "hotel_id": hotel_id
        })


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_sparkline_data(start_date, end_date, hotel_id=None):
    """Fetch daily KPI data for sparkline charts."""
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(SPARKLINE_SQL, conn, params={
            "start_date": start_date, "end_date": end_date, "hotel_id": hotel_id
        })


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def fetch_monthly_revenue(start_date, end_date, hotel_id=None):
    """Fetch revenue aggregated by calendar month for the bar chart."""
    with psycopg2.connect(DATABASE_URL) as conn:
        return pd.read_sql(MONTHLY_REVENUE_SQL, conn, params={
            "start_date": start_date, "end_date": end_date, "hotel_id": hotel_id
        })


def _aggregate(df):
    if df.empty:
        return None
    total_revenue = df["total_revenue"].sum()
    total_room_nights = df["room_nights"].sum()
    return {
        "total_revenue": total_revenue,
        "room_nights": total_room_nights,
        # ADR = total revenue / total room nights (weighted, không dùng mean của daily adr)
        "adr": float(total_revenue / total_room_nights) if total_room_nights else None,
        # occupancy và revpar đã được normalize theo room_count trong dbt, avg daily là đúng
        "occupancy": float(df["occupancy"].mean()),
        "revpar": float(df["revpar"].mean()),
        "cancellation_rate": float(df["cancellation_rate"].mean()),
    }


def fetch_executive_kpi_summary(start_date, end_date, hotel_id=None):
    """Current vs prior-period aggregates for 5 executive KPIs.
    WoW (7d) for ranges <=14 days, MoM (30d) for longer ranges.
    """
    current = fetch_executive_kpi_daily(start_date, end_date, hotel_id)
    range_days = (end_date - start_date).days + 1
    shift = timedelta(days=7 if range_days <= 14 else 30)
    prior = fetch_executive_kpi_daily(start_date - shift, end_date - shift, hotel_id)
    return _aggregate(current), _aggregate(prior)


def determine_status(metric_name, current_val, prior_val, target=None):
    """
    Determine executive status: on_track / at_risk / critical.
    Logic: if target provided, compare to target. Else compare to prior period.
    - on_track: >= target (or >= prior)
    - at_risk: 90-100% of target (or 95-100% of prior)
    - critical: < 90% of target (or < 95% of prior)
    """
    if target is not None and target > 0:
        pct = current_val / target
    elif prior_val is not None and prior_val > 0:
        pct = current_val / prior_val
    else:
        return "on_track"

    if pct >= 1.0:
        return "on_track"
    elif pct >= 0.95:
        return "at_risk"
    else:
        return "critical"