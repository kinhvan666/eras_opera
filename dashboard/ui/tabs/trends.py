import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily, fetch_revenue_actual
from ui.components import chart_wrapper
from ui.i18n import t

# Hex colors (CSS vars don't work inside Vega-Lite/SVG)
BLUE   = "#1D4ED8"
AMBER  = "#F59E0B"
GRAY   = "#ADB5BD"

VND_LABEL_EXPR = (
    "datum.value >= 1e9 ? format(datum.value / 1e9, '.1f') + 'B' : "
    "datum.value >= 1e6 ? format(datum.value / 1e6, '.0f') + 'M' : "
    "datum.value >= 1e3 ? format(datum.value / 1e3, '.0f') + 'K' : "
    "format(datum.value, ',.0f')"
)


def _fmt(v):
    if v >= 1e9: return f"{v/1e9:.2f}B"
    if v >= 1e6: return f"{v/1e6:.0f}M"
    if v >= 1e3: return f"{v/1e3:.0f}K"
    return f"{v:,.0f}"


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
        st.info(t("msg.no_data"))
        return

    df = df.copy()
    df["business_date"] = df["business_date"].astype(str)

    # Actual revenue from fct_folio_line (excl Tax) — same source as Revenue KPI tile
    df_actual = fetch_revenue_actual(start_date, end_date, hotel_id)
    if df_actual is not None and not df_actual.empty:
        df_rev_day = (df_actual[df_actual["revenue_category"] != "Tax"]
                      .groupby("revenue_date", as_index=False)["posted_amount"]
                      .sum()
                      .rename(columns={"posted_amount": "total_revenue",
                                       "revenue_date": "business_date"}))
        df_rev_day["business_date"] = df_rev_day["business_date"].astype(str)
    else:
        df_rev_day = pd.DataFrame(columns=["business_date", "total_revenue"])

    if "trend_view" not in st.session_state:
        st.session_state["trend_view"] = t("rev.by_month")
    by_month = st.radio(t("rev.view"), [t("rev.by_month"), t("rev.by_day")],
                        horizontal=True, label_visibility="collapsed", key="trend_view") == t("rev.by_month")

    if by_month:
        mdf = _monthly(df)
        mdf["_adr_label"] = mdf["adr"].apply(lambda v: _fmt(v) if pd.notna(v) else "")
        x_field = alt.X("month:N", title=t("axis.month"), sort=list(mdf["month"]))
        x_tooltip = alt.Tooltip("month:N", title=t("axis.month"))
        src = mdf

        # Revenue chart: monthly actual (fct_folio_line)
        if not df_rev_day.empty:
            df_rev_day["month"] = pd.to_datetime(df_rev_day["business_date"]).dt.to_period("M").astype(str)
            rev_src = df_rev_day.groupby("month", as_index=False)["total_revenue"].sum()
            rev_x = alt.X("month:N", title=t("axis.month"), sort=list(rev_src["month"]))
        else:
            rev_src = mdf
            rev_x = x_field
        rev_src = rev_src.copy()
        rev_src["_rev_label"] = rev_src["total_revenue"].apply(_fmt)
    else:
        src = df
        x_field = alt.X("business_date:T", title=t("axis.date"))
        x_tooltip = alt.Tooltip("business_date:T", title=t("axis.date"))

        # Revenue chart: daily actual (fct_folio_line)
        rev_src = df_rev_day if not df_rev_day.empty else df
        rev_x = (alt.X("business_date:T", title=t("axis.date"))
                 if not df_rev_day.empty else x_field)

    col1, col2 = st.columns(2)

    with col1:
        title = t("chart.revenue_by_month") if by_month else t("chart.revenue_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            bars = alt.Chart(rev_src).mark_bar(color=BLUE, opacity=0.8,
                                               cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                x=rev_x,
                y=alt.Y("total_revenue:Q", title=t("axis.revenue"), axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                tooltip=[x_tooltip, alt.Tooltip("total_revenue:Q", format=",.0f", title=t("axis.revenue"))],
            ).properties(height=280)
            if by_month and "_rev_label" in rev_src.columns:
                labels = bars.mark_text(align="center", baseline="bottom", dy=-4, fontSize=10).encode(
                    text=alt.Text("_rev_label:N")
                )
                bars = bars + labels
            st.altair_chart(bars, use_container_width=True)

    with col2:
        title = t("chart.occupancy_by_month") if by_month else t("chart.occupancy_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("occupancy:Q", title=t("axis.occupancy"), axis=alt.Axis(format="%")),
                    tooltip=[x_tooltip, alt.Tooltip("occupancy:Q", format=".1%", title=t("axis.occupancy"))],
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
                    y=alt.Y("occupancy:Q", title=t("axis.occupancy"), axis=alt.Axis(format="%")),
                )
                line = alt.Chart(src).mark_line(color=BLUE, strokeWidth=2).encode(
                    x="business_date:T",
                    y="occupancy:Q",
                    tooltip=[x_tooltip, alt.Tooltip("occupancy:Q", format=".1%", title=t("axis.occupancy"))],
                )
                st.altair_chart((area + line).properties(height=280), use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        title = t("chart.adr_by_month") if by_month else t("chart.adr_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("adr:Q", title=t("axis.adr"), axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                    tooltip=[x_tooltip, alt.Tooltip("adr:Q", format=",.0f", title=t("axis.adr"))],
                )
                st.altair_chart(
                    (base.mark_line(color=BLUE, strokeWidth=2)
                     + base.mark_point(color=BLUE, size=60, filled=True)
                     + base.mark_text(dy=-12, fontSize=10).encode(
                          text=alt.Text("_adr_label:N")
                      )).properties(height=280),
                    use_container_width=True,
                )
            else:
                st.altair_chart(
                    alt.Chart(src).mark_bar(color=BLUE, opacity=0.8,
                                             cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=x_field,
                        y=alt.Y("adr:Q", title=t("axis.adr"), axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                        tooltip=[x_tooltip, alt.Tooltip("adr:Q", format=",.0f", title=t("axis.adr"))],
                    ).properties(height=280),
                    use_container_width=True,
                )

    with col4:
        title = t("chart.cancel_by_month") if by_month else t("chart.cancel_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("cancellation_rate:Q", title=t("axis.cancel"),
                            axis=alt.Axis(format="%")),
                    tooltip=[x_tooltip, alt.Tooltip("cancellation_rate:Q", format=".1%", title=t("axis.cancel"))],
                )
                st.altair_chart(
                    (base.mark_line(color=AMBER, strokeWidth=2)
                     + base.mark_point(color=AMBER, size=60, filled=True)
                     + base.mark_text(dy=-12, fontSize=10).encode(
                          text=alt.Text("cancellation_rate:Q", format=".1%")
                      )).properties(height=280),
                    use_container_width=True,
                )
            else:
                st.altair_chart(
                    alt.Chart(src).mark_bar(color=AMBER, opacity=0.75,
                                             cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=x_field,
                        y=alt.Y("cancellation_rate:Q", title=t("axis.cancel"),
                                axis=alt.Axis(format="%")),
                        tooltip=[x_tooltip, alt.Tooltip("cancellation_rate:Q", format=".1%", title=t("axis.cancel"))],
                    ).properties(height=280),
                    use_container_width=True,
                )
