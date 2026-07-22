import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily, fetch_revenue_actual
from ui.components import chart_wrapper
from ui.i18n import t

from ui.theme import chart_colors

VND_LABEL_EXPR = (
    "datum.value >= 1e9 ? format(datum.value / 1e9, '.1f') + 'B' : "
    "datum.value >= 1e6 ? format(datum.value / 1e6, '.0f') + 'M' : "
    "datum.value >= 1e3 ? format(datum.value / 1e3, '.0f') + 'K' : "
    "format(datum.value, ',.0f')"
)


def _fmt(v):
    if v >= 1e9: return f"₫{v/1e9:.1f}B"
    if v >= 1e6: return f"₫{v/1e6:.0f}M"
    if v >= 1e3: return f"₫{v/1e3:.0f}K"
    return f"₫{v:,.0f}"


def _monthly(df, start_date=None, end_date=None):
    """Aggregate daily df to monthly for all KPIs."""
    df2 = df.copy()
    df2["month"] = pd.to_datetime(df2["business_date"]).dt.to_period("M").astype(str)
    agg = df2.groupby("month", as_index=False).agg(
        total_revenue=("total_revenue", "sum"),
        room_nights=("room_nights", "sum"),
        occupancy=("occupancy", "mean"),
        cancellation_rate=("cancellation_rate", "mean"),
        min_date=("business_date", "min"),
        max_date=("business_date", "max"),
    )
    # Weighted ADR = total revenue / total room nights
    agg["adr"] = agg["total_revenue"] / agg["room_nights"].replace(0, float("nan"))

    def check_partial(row):
        m = pd.Period(row["month"])
        first_day = str(m.start_time.date())
        last_day = str(m.end_time.date())
        s_date = str(start_date) if start_date else row["min_date"]
        e_date = str(end_date) if end_date else row["max_date"]
        return (s_date > first_day) or (e_date < last_day)

    agg["is_partial"] = agg.apply(check_partial, axis=1)
    return agg.sort_values("month")


def _with_ma7(df, col):
    """Thêm cột {col}_ma7 = trung bình trượt 7 ngày (min_periods=1)."""
    out = df.sort_values("business_date").copy()
    out[f"{col}_ma7"] = out[col].rolling(7, min_periods=1).mean()
    return out


def _weekend_bands(df):
    """DataFrame các ngày T7/CN để vẽ dải mờ: cột band_start, band_end (ngày +1)."""
    d = pd.to_datetime(df["business_date"])
    wk = df.loc[d.dt.dayofweek >= 5, ["business_date"]].copy()
    wk["band_start"] = pd.to_datetime(wk["business_date"])
    wk["band_end"] = wk["band_start"] + pd.Timedelta(days=1)
    return wk


def _weekly_cancel(df):
    """Gộp cancellation_rate theo tuần (nhãn = thứ Hai đầu tuần), mean."""
    d = df.copy()
    d["week"] = pd.to_datetime(d["business_date"]).dt.to_period("W-SUN").dt.start_time
    return d.groupby("week", as_index=False)["cancellation_rate"].mean()


def draw(start_date, end_date, hotel_id=None):
    C = chart_colors()
    df = fetch_kpi_daily(start_date, end_date, hotel_id)
    if df.empty:
        st.info(t("msg.no_data"))
        return

    df = df.copy()
    df["business_date"] = df["business_date"].astype(str)

    # Actual revenue from fct_folio_line (excl Tax) — same source as Revenue KPI tile
    df_actual = fetch_revenue_actual(start_date, end_date, hotel_id)
    if df_actual is not None and not df_actual.empty:
        df_rev_day = (df_actual[df_actual["revenue_category"] == "Room"]
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
        mdf = _monthly(df, start_date, end_date)
        def make_kpi_label(row, kpi_val, is_pct=False):
            if pd.isna(kpi_val): return ""
            fmt = f"{kpi_val:.1%}" if is_pct else _fmt(kpi_val)
            if row.get("is_partial"):
                fmt += "*"
            return fmt

        mdf["_adr_label"] = mdf.apply(lambda r: make_kpi_label(r, r["adr"]), axis=1)
        mdf["_occ_label"] = mdf.apply(lambda r: make_kpi_label(r, r["occupancy"], True), axis=1)
        mdf["_cancel_label"] = mdf.apply(lambda r: make_kpi_label(r, r["cancellation_rate"], True), axis=1)
        x_field = alt.X("month:N", title=t("axis.month"), sort=list(mdf["month"]),
                        axis=alt.Axis(labelAngle=0, labelColor=C["text_label"], titleColor=C["text_label"], labelFontSize=11, labelFontWeight=600))
        x_tooltip = alt.Tooltip("month:N", title=t("axis.month"))
        src = mdf

        # Revenue chart: monthly actual (fct_folio_line)
        if not df_rev_day.empty:
            df_rev_day["month"] = pd.to_datetime(df_rev_day["business_date"]).dt.to_period("M").astype(str)
            rev_src = df_rev_day.groupby("month", as_index=False)["total_revenue"].sum().sort_values("month")
            rev_x = alt.X("month:N", title=t("axis.month"), sort=list(rev_src["month"]),
                          axis=alt.Axis(labelAngle=0, labelColor=C["text_label"], titleColor=C["text_label"], labelFontSize=11, labelFontWeight=600))
            rev_src = pd.merge(rev_src, mdf[["month", "is_partial"]], on="month", how="left")
            rev_src["is_partial"] = rev_src["is_partial"].fillna(False)
        else:
            rev_src = mdf
            rev_x = x_field
        rev_src = rev_src.copy()
        rev_src["_mom"] = rev_src["total_revenue"].pct_change()
        
        def make_rev_label(row):
            fmt = _fmt(row["total_revenue"])
            if pd.notna(row["_mom"]):
                pct = row["_mom"] * 100
                fmt += f" ({'+' if pct > 0 else ''}{pct:.0f}%)"
            if row.get("is_partial"):
                fmt += "*"
            return fmt
            
        rev_src["_rev_label"] = rev_src.apply(make_rev_label, axis=1)
    else:
        src = df
        x_field = alt.X("business_date:T", title=t("axis.date"),
                        axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"]))
        x_tooltip = alt.Tooltip("business_date:T", title=t("axis.date"))

        # Revenue chart: daily actual (fct_folio_line)
        rev_src = df_rev_day if not df_rev_day.empty else df
        rev_x = (alt.X("business_date:T", title=t("axis.date"),
                       axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"]))
                 if not df_rev_day.empty else x_field)

    col1, col2 = st.columns(2)

    with col1:
        title = t("chart.room_revenue_by_month") if by_month else t("chart.room_revenue_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                bars = alt.Chart(rev_src).mark_bar(
                    color=C["primary"], cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                ).encode(
                    x=rev_x,
                    y=alt.Y("total_revenue:Q", title=t("axis.revenue"),
                            axis=alt.Axis(labelExpr=VND_LABEL_EXPR, labelColor=C["text_label"], titleColor=C["text_label"])),
                    opacity=alt.condition("datum.is_partial", alt.value(0.75), alt.value(1.0)),
                    tooltip=[x_tooltip, alt.Tooltip("total_revenue:Q", format=",.0f", title=t("axis.revenue"))],
                ).properties(height=280)
                if "_rev_label" in rev_src.columns:
                    labels = alt.Chart(rev_src).mark_text(align="center", baseline="bottom", dy=-4, fontSize=12, fontWeight=700).encode(
                        x=rev_x,
                        y=alt.Y("total_revenue:Q"),
                        color=alt.value(C["text_label"]),
                        text=alt.Text("_rev_label:N")
                    )
                    st.altair_chart(alt.layer(bars, labels).resolve_scale(color='independent'), use_container_width=True)
                else:
                    st.altair_chart(bars, use_container_width=True)
            else:
                r_src = _with_ma7(rev_src, "total_revenue")
                wk = _weekend_bands(r_src)
                bands = alt.Chart(wk).mark_rect(color=C["band"], opacity=0.18).encode(
                    x="band_start:T", x2="band_end:T"
                )
                line = alt.Chart(r_src).mark_line(color=C["primary"], strokeWidth=1.5, opacity=0.35).encode(
                    x=rev_x,
                    y=alt.Y("total_revenue:Q", title=t("axis.revenue"),
                            axis=alt.Axis(labelExpr=VND_LABEL_EXPR, labelColor=C["text_label"], titleColor=C["text_label"])),
                    tooltip=[x_tooltip, alt.Tooltip("total_revenue:Q", format=",.0f", title=t("axis.revenue"))],
                )
                ma7 = alt.Chart(r_src).mark_line(color=C["primary"], strokeWidth=2.5, opacity=1.0).encode(
                    x=rev_x,
                    y=alt.Y("total_revenue_ma7:Q", title=t("axis.revenue")),
                    tooltip=[x_tooltip, alt.Tooltip("total_revenue_ma7:Q", format=",.0f", title=t("trend.ma7"))],
                )
                st.altair_chart((bands + line + ma7).properties(height=280), use_container_width=True)

    with col2:
        title = t("chart.occupancy_by_month") if by_month else t("chart.occupancy_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("occupancy:Q", title=t("axis.occupancy"),
                            axis=alt.Axis(format="%", labelColor=C["text_label"], titleColor=C["text_label"])),
                    tooltip=[x_tooltip, alt.Tooltip("occupancy:Q", format=".1%", title=t("axis.occupancy"))],
                )
                st.altair_chart(
                    (base.mark_line(color=C["primary"], strokeWidth=2.5)
                     + base.mark_point(color=C["primary"], size=70, filled=True)
                     + base.mark_text(dy=-12, fontSize=12, fontWeight=700, color=C["text_label"]).encode(
                          text=alt.Text("_occ_label:N")
                      )).properties(height=280),
                    use_container_width=True,
                )
            else:
                o_src = _with_ma7(src, "occupancy")
                wk = _weekend_bands(o_src)
                bands = alt.Chart(wk).mark_rect(color=C["band"], opacity=0.18).encode(
                    x="band_start:T", x2="band_end:T"
                )
                area = alt.Chart(o_src).mark_area(opacity=0.15, color=C["primary"]).encode(
                    x=x_field,
                    y=alt.Y("occupancy:Q", title=t("axis.occupancy"),
                            axis=alt.Axis(format="%", labelColor=C["text_label"], titleColor=C["text_label"])),
                )
                line = alt.Chart(o_src).mark_line(color=C["primary"], strokeWidth=1.5, opacity=0.35).encode(
                    x=x_field,
                    y=alt.Y("occupancy:Q", title=t("axis.occupancy"),
                            axis=alt.Axis(format="%", labelColor=C["text_label"], titleColor=C["text_label"])),
                    tooltip=[x_tooltip, alt.Tooltip("occupancy:Q", format=".1%", title=t("axis.occupancy"))],
                )
                ma7 = alt.Chart(o_src).mark_line(color=C["primary"], strokeWidth=2.5, opacity=1.0).encode(
                    x=x_field,
                    y=alt.Y("occupancy_ma7:Q", title=t("trend.ma7")),
                    tooltip=[x_tooltip, alt.Tooltip("occupancy_ma7:Q", format=".1%", title=t("trend.ma7"))],
                )
                st.altair_chart((bands + area + line + ma7).properties(height=280), use_container_width=True)
                st.caption(t("trend.weekend_note") + " · " + t("trend.ma7") + " = đường đậm")

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        title = t("chart.adr_by_month") if by_month else t("chart.adr_by_day")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("adr:Q", title=t("axis.adr"),
                            axis=alt.Axis(labelExpr=VND_LABEL_EXPR, labelColor=C["text_label"], titleColor=C["text_label"])),
                    tooltip=[x_tooltip, alt.Tooltip("adr:Q", format=",.0f", title=t("axis.adr"))],
                )
                st.altair_chart(
                    (base.mark_line(color=C["primary"], strokeWidth=2.5)
                     + base.mark_point(color=C["primary"], size=70, filled=True)
                     + base.mark_text(dy=-12, fontSize=12, fontWeight=700, color=C["text_label"]).encode(
                          text=alt.Text("_adr_label:N")
                      )).properties(height=280),
                    use_container_width=True,
                )
            else:
                a_src = src.copy()
                a_src["adr"] = a_src["adr"].replace(0, float("nan"))
                a_src = _with_ma7(a_src, "adr")
                wk = _weekend_bands(a_src)
                bands = alt.Chart(wk).mark_rect(color=C["band"], opacity=0.18).encode(
                    x="band_start:T", x2="band_end:T"
                )
                line = alt.Chart(a_src).mark_line(color=C["primary"], strokeWidth=1.5, opacity=0.35).encode(
                    x=x_field,
                    y=alt.Y("adr:Q", title=t("axis.adr"),
                            axis=alt.Axis(labelExpr=VND_LABEL_EXPR, labelColor=C["text_label"], titleColor=C["text_label"])),
                    tooltip=[x_tooltip, alt.Tooltip("adr:Q", format=",.0f", title=t("axis.adr"))],
                )
                ma7 = alt.Chart(a_src).mark_line(color=C["primary"], strokeWidth=2.5, opacity=1.0).encode(
                    x=x_field,
                    y=alt.Y("adr_ma7:Q", title=t("axis.adr")),
                    tooltip=[x_tooltip, alt.Tooltip("adr_ma7:Q", format=",.0f", title=t("trend.ma7"))],
                )
                st.altair_chart((bands + line + ma7).properties(height=280), use_container_width=True)

    with col4:
        title = t("chart.cancel_by_month") if by_month else t("chart.cancel_by_week")
        c = chart_wrapper(title, height=350)
        with c:
            if by_month:
                base = alt.Chart(src).encode(
                    x=x_field,
                    y=alt.Y("cancellation_rate:Q", title=t("axis.cancel"),
                            axis=alt.Axis(format="%", labelColor=C["text_label"], titleColor=C["text_label"])),
                    tooltip=[x_tooltip, alt.Tooltip("cancellation_rate:Q", format=".1%", title=t("axis.cancel"))],
                )
                st.altair_chart(
                    (base.mark_line(color=C["warn"], strokeWidth=2.5)
                     + base.mark_point(color=C["warn"], size=70, filled=True)
                     + base.mark_text(dy=-12, fontSize=12, fontWeight=700, color=C["text_label"]).encode(
                          text=alt.Text("_cancel_label:N")
                      )).properties(height=280),
                    use_container_width=True,
                )
            else:
                c_src = _weekly_cancel(src)
                # Trục thời gian liên tục → cột mặc định rất mảnh; đặt bề rộng theo số tuần
                bar_size = max(8, min(40, int(600 / max(len(c_src), 1) * 0.6)))
                st.altair_chart(
                    alt.Chart(c_src).mark_bar(color=C["warn"], opacity=0.75, size=bar_size,
                                             cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=alt.X("week:T", title=t("axis.date"),
                                axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                        y=alt.Y("cancellation_rate:Q", title=t("axis.cancel"),
                                axis=alt.Axis(format="%", labelColor=C["text_label"], titleColor=C["text_label"])),
                        tooltip=[alt.Tooltip("week:T", title=t("axis.date")), alt.Tooltip("cancellation_rate:Q", format=".1%", title=t("axis.cancel"))],
                    ).properties(height=280),
                    use_container_width=True,
                )

    if by_month and mdf.get("is_partial", pd.Series([False])).any():
        st.caption(t("trend.partial_month_note"))


