import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily
from ui.components import chart_wrapper

# Hex colors (CSS vars don't work inside Vega-Lite/SVG)
BLUE   = "#0B5ED7"
GREEN  = "#157347"
RED    = "#DC3545"
GRAY   = "#ADB5BD"


def draw(start_date, end_date, hotel_id=None):
    df = fetch_kpi_daily(start_date, end_date, hotel_id)
    if df.empty:
        st.info("No data for selected range.")
        return

    df = df.copy()
    df["business_date"] = df["business_date"].astype(str)

    col1, col2 = st.columns(2)

    with col1:
        c = chart_wrapper("Occupancy by Day", height=350)
        with c:
            area = alt.Chart(df).mark_area(opacity=0.2, color=BLUE).encode(
                x=alt.X("business_date:T", title="Date"),
                y=alt.Y("occupancy:Q", title="Occupancy", axis=alt.Axis(format="%")),
            )
            line = alt.Chart(df).mark_line(color=BLUE, strokeWidth=2).encode(
                x="business_date:T",
                y="occupancy:Q",
                tooltip=[alt.Tooltip("business_date:T", title="Date"),
                         alt.Tooltip("occupancy:Q", format=".1%", title="Occupancy")],
            )
            st.altair_chart((area + line).properties(height=280), use_container_width=True)

    with col2:
        c = chart_wrapper("Revenue by Day", height=350)
        with c:
            st.altair_chart(
                alt.Chart(df).mark_bar(color=BLUE, opacity=0.8,
                                       cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                    x=alt.X("business_date:T", title="Date"),
                    y=alt.Y("total_revenue:Q", title="Revenue (₫)", axis=alt.Axis(format=",.0f")),
                    tooltip=[alt.Tooltip("business_date:T", title="Date"),
                             alt.Tooltip("total_revenue:Q", format=",.0f", title="Revenue ₫")],
                ).properties(height=280),
                use_container_width=True,
            )

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        c = chart_wrapper("ADR by Day", height=350)
        with c:
            st.altair_chart(
                alt.Chart(df).mark_bar(color=GREEN, opacity=0.8,
                                       cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                    x=alt.X("business_date:T", title="Date"),
                    y=alt.Y("adr:Q", title="ADR (₫)", axis=alt.Axis(format=",.0f")),
                    tooltip=[alt.Tooltip("business_date:T", title="Date"),
                             alt.Tooltip("adr:Q", format=",.0f", title="ADR ₫"),
                             alt.Tooltip("revpar:Q", format=",.0f", title="RevPAR ₫")],
                ).properties(height=280),
                use_container_width=True,
            )

    with col4:
        c = chart_wrapper("Cancellation Rate by Day", height=350)
        with c:
            st.altair_chart(
                alt.Chart(df).mark_bar(color=RED, opacity=0.75,
                                       cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                    x=alt.X("business_date:T", title="Date"),
                    y=alt.Y("cancellation_rate:Q", title="Cancellation Rate",
                            axis=alt.Axis(format="%")),
                    tooltip=[alt.Tooltip("business_date:T", title="Date"),
                             alt.Tooltip("cancellation_rate:Q", format=".1%", title="Canc. Rate")],
                ).properties(height=280),
                use_container_width=True,
            )
