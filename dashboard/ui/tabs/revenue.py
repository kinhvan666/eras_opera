import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_revenue_breakdown, fetch_revenue_actual
from ui.components import chart_wrapper

# Stacked chart — Option 2 Analogous/Categorical
ROOM_COLOR    = "#2563EB"  # Deep Blue
FNB_COLOR     = "#0D9488"  # Teal
SC_COLOR      = "#F59E0B"  # Amber
OTHER_COLOR   = "#6B7280"  # Cool Gray
SUB_BAR_COLOR = "#2563EB"  # single color for all sub-charts

# Vega-Lite expression: abbreviate VND values on axes
VND_LABEL_EXPR = (
    "datum.value >= 1e9 ? format(datum.value / 1e9, '.1f') + 'B' : "
    "datum.value >= 1e6 ? format(datum.value / 1e6, '.0f') + 'M' : "
    "datum.value >= 1e3 ? format(datum.value / 1e3, '.0f') + 'K' : "
    "format(datum.value, ',.0f')"
)

CATEGORY_ORDER  = ["Room", "FnB", "ServiceCharge", "Other"]
CATEGORY_COLORS = [ROOM_COLOR, FNB_COLOR, SC_COLOR, OTHER_COLOR]


def _fmt_label(v):
    if v >= 1e9: return f"₫{v/1e9:.1f}B"
    if v >= 1e6: return f"₫{v/1e6:.0f}M"
    if v >= 1e3: return f"₫{v/1e3:.0f}K"
    return f"₫{v:,.0f}"


def _hbar(data, x_col, y_col, color, x_title, y_title):
    """Horizontal bar chart sorted descending by value."""
    data = data.copy().sort_values(x_col, ascending=True)
    data["_label"] = data[x_col].apply(_fmt_label)
    bars = alt.Chart(data).mark_bar(
        color=color, opacity=0.85,
        cornerRadiusTopRight=2, cornerRadiusBottomRight=2
    ).encode(
        y=alt.Y(f"{y_col}:N", sort="-x", title=y_title),
        x=alt.X(f"{x_col}:Q", title=x_title,
                axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
        tooltip=[
            alt.Tooltip(f"{y_col}:N", title=y_title),
            alt.Tooltip(f"{x_col}:Q", format=",.0f", title=x_title),
        ],
    )
    labels = bars.mark_text(align="left", dx=4, fontSize=10).encode(
        text=alt.Text("_label:N")
    )
    return (bars + labels).properties(height=max(180, len(data) * 36))


def draw(start_date, end_date, hotel_id=None):
    # ── Revenue by Day — actual, stacked by category ────────────────────────
    df_actual = fetch_revenue_actual(start_date, end_date, hotel_id)

    if "rev_tab_view" not in st.session_state:
        st.session_state["rev_tab_view"] = "By Month"
    by_month = st.radio(
        "View", ["By Month", "By Day"],
        horizontal=True, label_visibility="collapsed", key="rev_tab_view"
    ) == "By Month"

    if df_actual is not None and not df_actual.empty:
        df_chart = df_actual[df_actual["revenue_category"] != "Tax"].copy()

        if by_month:
            df_chart["month"] = (
                pd.to_datetime(df_chart["revenue_date"]).dt.to_period("M").astype(str)
            )
            src = df_chart.groupby(
                ["month", "revenue_category"], as_index=False
            )["posted_amount"].sum()
            x_enc     = alt.X("month:N", title="Month",
                               sort=sorted(src["month"].unique()))
            x_tooltip = alt.Tooltip("month:N", title="Month")
        else:
            src       = df_chart
            x_enc     = alt.X("revenue_date:T", title="Date")
            x_tooltip = alt.Tooltip("revenue_date:T", title="Date",
                                     format="%d/%m/%Y")

        title = "Revenue by Month" if by_month else "Revenue by Day"
        with chart_wrapper(title, height=360):
            bars = alt.Chart(src).mark_bar(
                cornerRadiusTopLeft=2, cornerRadiusTopRight=2
            ).encode(
                x=x_enc,
                y=alt.Y("sum(posted_amount):Q", title="Revenue (₫)",
                        axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                color=alt.Color(
                    "revenue_category:N", title="Category",
                    scale=alt.Scale(domain=CATEGORY_ORDER, range=CATEGORY_COLORS),
                ),
                order=alt.Order("revenue_category:N", sort="ascending"),
                tooltip=[
                    x_tooltip,
                    alt.Tooltip("revenue_category:N", title="Category"),
                    alt.Tooltip("sum(posted_amount):Q", format=",.0f",
                                title="Revenue ₫"),
                ],
            ).properties(height=290)
            st.altair_chart(bars, use_container_width=True)
    else:
        st.info("No posting data for selected range.")

    st.divider()

    # ── Breakdown by segment / rate plan / room type (booking data) ─────────
    bdf = fetch_revenue_breakdown(start_date, end_date, hotel_id)
    if bdf.empty:
        st.info("No breakdown data for selected range.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        seg = (bdf.groupby("market_code", as_index=False)["revenue"]
                  .sum().sort_values("revenue", ascending=False))
        with chart_wrapper("Revenue by Market Segment", height=300):
            st.altair_chart(
                _hbar(seg, "revenue", "market_code", SUB_BAR_COLOR, "Revenue ₫", "Segment"),
                use_container_width=True,
            )

    with col2:
        rate = (bdf.groupby("rate_plan_code", as_index=False)["revenue"]
                   .sum().sort_values("revenue", ascending=False))
        with chart_wrapper("Revenue by Rate Plan", height=300):
            st.altair_chart(
                _hbar(rate, "revenue", "rate_plan_code", SUB_BAR_COLOR,
                      "Revenue ₫", "Rate Plan"),
                use_container_width=True,
            )

    with col3:
        room = (bdf.groupby("room_type", as_index=False)["revenue"]
                   .sum().sort_values("revenue", ascending=False))
        with chart_wrapper("Revenue by Room Type", height=300):
            st.altair_chart(
                _hbar(room, "revenue", "room_type", SUB_BAR_COLOR,
                      "Revenue ₫", "Room Type"),
                use_container_width=True,
            )

    st.caption(
        "Market segment, rate plan, and room type breakdowns are based on booking data "
        "(fct_reservation_night · night_amount)."
    )
