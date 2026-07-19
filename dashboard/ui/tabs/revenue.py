import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily, fetch_revenue_breakdown, fetch_revenue_actual
from ui.components import chart_wrapper

BLUE  = "#0B5ED7"
GREEN = "#157347"


def _monthly(df):
    df2 = df.copy()
    df2["month"] = pd.to_datetime(df2["business_date"]).dt.to_period("M").astype(str)
    return (df2.groupby("month", as_index=False)["total_revenue"].sum()
               .sort_values("month"))


def _hbar(data, x_col, y_col, color, x_title, y_title):
    """Horizontal bar chart sorted descending by value."""
    data = data.copy().sort_values(x_col, ascending=True)
    bars = alt.Chart(data).mark_bar(color=color, opacity=0.85,
                                     cornerRadiusTopRight=2, cornerRadiusBottomRight=2).encode(
        y=alt.Y(f"{y_col}:N", sort="-x", title=y_title),
        x=alt.X(f"{x_col}:Q", title=x_title, axis=alt.Axis(format=",.0f")),
        tooltip=[alt.Tooltip(f"{y_col}:N", title=y_title),
                 alt.Tooltip(f"{x_col}:Q", format=",.0f", title=x_title)],
    )
    labels = bars.mark_text(align="left", dx=4, fontSize=10).encode(
        text=alt.Text(f"{x_col}:Q", format=",.0f")
    )
    return (bars + labels).properties(height=max(180, len(data) * 36))


def draw(start_date, end_date, hotel_id=None):
    df = fetch_kpi_daily(start_date, end_date, hotel_id)
    if df.empty:
        st.info("No data for selected range.")
        return

    df = df.copy()
    df["business_date"] = df["business_date"].astype(str)

    # ── Trend ──────────────────────────────────────────────────────────────
    by_month = st.radio("View", ["By Day", "By Month"],
                        horizontal=True, label_visibility="collapsed",
                        key="rev_tab_view") == "By Month"

    if by_month:
        mdf = _monthly(df)
        x_field = alt.X("month:N", title="Month", sort=list(mdf["month"]))
        x_tooltip = alt.Tooltip("month:N", title="Month")
        src = mdf
    else:
        src = df
        x_field = alt.X("business_date:T", title="Date")
        x_tooltip = alt.Tooltip("business_date:T", title="Date")

    title = "Revenue by Month" if by_month else "Revenue by Day"
    c = chart_wrapper(title, height=360)
    with c:
        bars = alt.Chart(src).mark_bar(color=BLUE, opacity=0.85,
                                        cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
            x=x_field,
            y=alt.Y("total_revenue:Q", title="Revenue (₫)", axis=alt.Axis(format=",.0f")),
            tooltip=[x_tooltip, alt.Tooltip("total_revenue:Q", format=",.0f", title="Revenue ₫")],
        ).properties(height=290)
        if by_month:
            labels = bars.mark_text(align="center", baseline="bottom", dy=-4, fontSize=11).encode(
                text=alt.Text("total_revenue:Q", format=",.0f")
            )
            bars = bars + labels
        st.altair_chart(bars, use_container_width=True)

    st.divider()

    # ── Breakdown ───────────────────────────────────────────────────────────
    bdf = fetch_revenue_breakdown(start_date, end_date, hotel_id)
    if bdf.empty:
        st.info("No breakdown data for selected range.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        seg = bdf.groupby("market_code", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
        c = chart_wrapper("Revenue by Market Segment", height=300)
        with c:
            st.altair_chart(_hbar(seg, "revenue", "market_code", BLUE,
                                  "Revenue ₫", "Segment"),
                            use_container_width=True)

    with col2:
        rate = bdf.groupby("rate_plan_code", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
        c = chart_wrapper("Revenue by Rate Plan", height=300)
        with c:
            st.altair_chart(_hbar(rate, "revenue", "rate_plan_code", GREEN,
                                  "Revenue ₫", "Rate Plan"),
                            use_container_width=True)

    with col3:
        room = bdf.groupby("room_type", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
        c = chart_wrapper("Revenue by Room Type", height=300)
        with c:
            st.altair_chart(_hbar(room, "revenue", "room_type", "#6F42C1",
                                  "Revenue ₫", "Room Type"),
                            use_container_width=True)

    st.divider()

    # ── Actual Revenue from Cashiering Postings ─────────────────────────────
    st.subheader("Actual Revenue from Postings (Cashiering)")
    st.caption("Real charges posted to folios. Differs from estimated room revenue above which uses booking data.")
    df_actual = fetch_revenue_actual(start_date, end_date, hotel_id)
    if df_actual is None or df_actual.empty:
        st.info("No posting data for this date range.")
    else:
        st.metric("Total (₫)", f"₫{df_actual['posted_amount'].sum():,.0f}")
        chart = alt.Chart(df_actual).mark_bar().encode(
            x=alt.X("revenue_date:T", title="Date"),
            y=alt.Y("sum(posted_amount):Q", title="Revenue (₫)"),
            color=alt.Color("revenue_category:N", title="Category"),
            tooltip=["revenue_date:T", "revenue_category:N", "posted_amount:Q"],
        )
        with chart_wrapper("Actual Revenue by Category", height=300):
            st.altair_chart(chart, use_container_width=True)
