import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_revenue_breakdown, fetch_revenue_actual
from ui.components import chart_wrapper
from ui.i18n import t

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
    df_actual = fetch_revenue_actual(start_date, end_date, hotel_id)
    bdf = fetch_revenue_breakdown(start_date, end_date, hotel_id)

    if "rev_tab_view" not in st.session_state:
        st.session_state["rev_tab_view"] = t("rev.by_month")
    by_month = st.radio(
        t("rev.view"), [t("rev.by_month"), t("rev.by_day")],
        horizontal=True, label_visibility="collapsed", key="rev_tab_view"
    ) == t("rev.by_month")

    # ── Row 1: Revenue trend + Market Segment ───────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        if df_actual is not None and not df_actual.empty:
            df_chart = df_actual[df_actual["revenue_category"] != "Tax"].copy()
            if by_month:
                df_chart["month"] = (
                    pd.to_datetime(df_chart["revenue_date"]).dt.to_period("M").astype(str)
                )
                src = df_chart.groupby(
                    ["month", "revenue_category"], as_index=False
                )["posted_amount"].sum()
                x_enc     = alt.X("month:N", title=t("axis.month"),
                                    sort=sorted(src["month"].unique()))
                x_tooltip = alt.Tooltip("month:N", title=t("axis.month"))
            else:
                src       = df_chart
                x_enc     = alt.X("revenue_date:T", title=t("axis.date"))
                x_tooltip = alt.Tooltip("revenue_date:T", title=t("axis.date"),
                                         format="%d/%m/%Y")
            title = t("chart.revenue_by_month") if by_month else t("chart.revenue_by_day")
            with chart_wrapper(title, height=340):
                # Pre-compute totals for label layer
                x_col = "month" if by_month else "revenue_date"
                totals = src.groupby(x_col, as_index=False)["posted_amount"].sum()
                totals["_label"] = totals["posted_amount"].apply(_fmt_label)
                x_enc_tot = alt.X(f"{x_col}:N", title=t("axis.month") if by_month else t("axis.date"),
                                    sort=sorted(src[x_col].unique()) if by_month else None)
                y_max = totals["posted_amount"].max() * 1.15

                bars = alt.Chart(src).mark_bar(
                    cornerRadiusTopLeft=2, cornerRadiusTopRight=2
                ).encode(
                    x=x_enc,
                    y=alt.Y("sum(posted_amount):Q", title=t("axis.revenue"),
                            axis=alt.Axis(labelExpr=VND_LABEL_EXPR),
                            scale=alt.Scale(domainMax=y_max)),
                    color=alt.Color(
                        "revenue_category:N", title=t("axis.category"),
                        scale=alt.Scale(domain=CATEGORY_ORDER, range=CATEGORY_COLORS),
                    ),
                    order=alt.Order("revenue_category:N", sort="ascending"),
                    tooltip=[
                        x_tooltip,
                        alt.Tooltip("revenue_category:N", title=t("axis.category")),
                        alt.Tooltip("sum(posted_amount):Q", format=",.0f",
                                    title=t("axis.revenue")),
                    ],
                ).properties(height=270)

                if by_month:
                    labels = alt.Chart(totals).mark_text(
                        align="center", baseline="bottom", dy=-4, fontSize=10, color="#374151"
                    ).encode(
                        x=x_enc_tot,
                        y=alt.Y("posted_amount:Q"),
                        text=alt.Text("_label:N"),
                    )
                    st.altair_chart(bars + labels, use_container_width=True)
                else:
                    st.altair_chart(bars, use_container_width=True)
        else:
            st.info(t("msg.no_posting"))

    with col2:
        if not bdf.empty:
            seg = (bdf.groupby("market_code", as_index=False)["revenue"]
                      .sum().sort_values("revenue", ascending=False))
            with chart_wrapper(t("chart.revenue_by_segment"), height=340):
                st.altair_chart(
                    _hbar(seg, "revenue", "market_code", SUB_BAR_COLOR, t("axis.revenue"), t("axis.segment")),
                    use_container_width=True,
                )

    # ── Row 2: Rate Plan + Room Type ────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        if not bdf.empty:
            rate = (bdf.groupby("rate_plan_code", as_index=False)["revenue"]
                       .sum().sort_values("revenue", ascending=False))
            with chart_wrapper(t("chart.revenue_by_rateplan"), height=340):
                st.altair_chart(
                    _hbar(rate, "revenue", "rate_plan_code", SUB_BAR_COLOR,
                          t("axis.revenue"), t("axis.rate_plan")),
                    use_container_width=True,
                )

    with col4:
        if not bdf.empty:
            room = (bdf.groupby("room_type", as_index=False)["revenue"]
                       .sum().sort_values("revenue", ascending=False))
            with chart_wrapper(t("chart.revenue_by_roomtype"), height=340):
                st.altair_chart(
                    _hbar(room, "revenue", "room_type", SUB_BAR_COLOR,
                          t("axis.revenue"), t("axis.room_type")),
                    use_container_width=True,
                )

    if bdf.empty:
        st.info(t("msg.no_breakdown"))
