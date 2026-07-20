import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily
from ui.components import chart_wrapper

# Hex colors (CSS vars don't work inside Vega-Lite/SVG)
BLUE   = "#0B5ED7"
GREEN  = "#157347"
RED    = "#DC3545"
GRAY   = "#ADB5BD"

VND_LABEL_EXPR = (
    "datum.value >= 1e9 ? format(datum.value / 1e9, '.1f') + 'B' : "
    "datum.value >= 1e6 ? format(datum.value / 1e6, '.0f') + 'M' : "
    "datum.value >= 1e3 ? format(datum.value / 1e3, '.0f') + 'K' : "
    "format(datum.value, ',.0f')"
)


def _monthly(df):
    """Aggregate daily df to monthly for all KPIs."""
    df2 = df.copy()
    df2["month"] = pd.to_datetime(df2["business_date"]).dt.to_period("M").astype(str)
    agg = df2.groupby("month", as_index=False).agg(
        total_revenue=("total_revenue", "sum"),
        room_nights=("room_nights", "sum"),
        occupancy=("occupancy", "mean"),
        cancellation_rate=("cancellation_rate", "mean"),
    )
    # Weighted ADR = total revenue / total room nights
    agg["adr"] = agg["total_revenue"] / agg["room_nights"].replace(0, float("nan"))
    return agg.sort_values("month")


def draw(start_date, end_date, hotel_id=None):
    df = fetch_kpi_daily(start_date, end_date, hotel_id)
    if df.empty:
        st.info("No data for selected range.")
        return

    df = df.copy()
    df["business_date"] = df["business_date"].astype(str)

    if "trend_view" not in st.session_state:
        st.session_state["trend_view"] = "By Month"
    by_month = st.radio("View", ["By Month", "By Day"],
                        horizontal=True, label_visibility="collapsed", key="trend_view") == "By Month"

    if by_month:
        mdf = _monthly(df)
        x_field = alt.X("month:N", title="Month", sort=list(mdf["month"]))
        x_tooltip = alt.Tooltip("month:N", title="Month")
        src = mdf
    else:
        src = df
        x_field = alt.X("business_date:T", title="Date")
        x_tooltip = alt.Tooltip("business_date:T", title="Date")

    col1, col2 = st.columns(2)

    with col1:
        title = "Revenue by Month" if by_month else "Revenue by Day"
        c = chart_wrapper(title, height=350)
        with c:
            bars = alt.Chart(src).mark_bar(color=BLUE, opacity=0.8,
                                            cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                x=x_field,
                y=alt.Y("total_revenue:Q", title="Revenue (₫)", axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                tooltip=[x_tooltip, alt.Tooltip("total_revenue:Q", format=",.0f", title="Revenue ₫")],
            ).properties(height=280)
            if by_month:
                labels = bars.mark_text(align="center", baseline="bottom", dy=-4, fontSize=10).encode(
                    text=alt.Text("total_revenue:Q", format="~s")
                )
                bars = bars + labels
            st.altair_chart(bars, use_container_width=True)

    with col2:
        title = "Occupancy by Month" if by_month else "Occupancy by Day"
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("occupancy:Q", title="Occupancy", axis=alt.Axis(format="%")),
                    tooltip=[x_tooltip, alt.Tooltip("occupancy:Q", format=".1%", title="Occupancy")],
                )
                st.altair_chart(
                    (base.mark_line(color=BLUE, strokeWidth=2)
                     + base.mark_point(color=BLUE, size=60, filled=True)
                     + base.mark_text(dy=-12, fontSize=10).encode(
                         text=alt.Text("occupancy:Q", format=".1%")
                     )).properties(height=280),
                    use_container_width=True,
                )
            else:
                area = alt.Chart(src).mark_area(opacity=0.2, color=BLUE).encode(
                    x=x_field,
                    y=alt.Y("occupancy:Q", title="Occupancy", axis=alt.Axis(format="%")),
                )
                line = alt.Chart(src).mark_line(color=BLUE, strokeWidth=2).encode(
                    x="business_date:T",
                    y="occupancy:Q",
                    tooltip=[x_tooltip, alt.Tooltip("occupancy:Q", format=".1%", title="Occupancy")],
                )
                st.altair_chart((area + line).properties(height=280), use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        title = "ADR by Month" if by_month else "ADR by Day"
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("adr:Q", title="ADR (₫)", axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                    tooltip=[x_tooltip, alt.Tooltip("adr:Q", format=",.0f", title="ADR ₫")],
                )
                st.altair_chart(
                    (base.mark_line(color=GREEN, strokeWidth=2)
                     + base.mark_point(color=GREEN, size=60, filled=True)
                     + base.mark_text(dy=-12, fontSize=10).encode(
                         text=alt.Text("adr:Q", format="~s")
                     )).properties(height=280),
                    use_container_width=True,
                )
            else:
                st.altair_chart(
                    alt.Chart(src).mark_bar(color=GREEN, opacity=0.8,
                                             cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=x_field,
                        y=alt.Y("adr:Q", title="ADR (₫)", axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                        tooltip=[x_tooltip, alt.Tooltip("adr:Q", format=",.0f", title="ADR ₫")],
                    ).properties(height=280),
                    use_container_width=True,
                )

    with col4:
        title = "Cancellation Rate by Month" if by_month else "Cancellation Rate by Day"
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("cancellation_rate:Q", title="Cancellation Rate",
                            axis=alt.Axis(format="%")),
                    tooltip=[x_tooltip, alt.Tooltip("cancellation_rate:Q", format=".1%", title="Canc. Rate")],
                )
                st.altair_chart(
                    (base.mark_line(color=RED, strokeWidth=2)
                     + base.mark_point(color=RED, size=60, filled=True)
                     + base.mark_text(dy=-12, fontSize=10).encode(
                         text=alt.Text("cancellation_rate:Q", format=".1%")
                     )).properties(height=280),
                    use_container_width=True,
                )
            else:
                st.altair_chart(
                    alt.Chart(src).mark_bar(color=RED, opacity=0.75,
                                             cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=x_field,
                        y=alt.Y("cancellation_rate:Q", title="Cancellation Rate",
                                axis=alt.Axis(format="%")),
                        tooltip=[x_tooltip, alt.Tooltip("cancellation_rate:Q", format=".1%", title="Canc. Rate")],
                    ).properties(height=280),
                    use_container_width=True,
                )
