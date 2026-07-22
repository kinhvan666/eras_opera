from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from data.repository import fetch_kpi_pacing, fetch_kpi_pickup
from ui.components import chart_wrapper
from ui.i18n import t

from ui.theme import chart_colors


def draw(start_date, end_date, hotel_id=None):
    C = chart_colors()
    # Pacing always looks forward — ignore the dashboard's historical date filter
    today = date.today()
    pace_start = today
    pace_end = today + timedelta(days=90)

    pace_df = fetch_kpi_pacing(pace_start, pace_end, hotel_id)
    pickup_df = fetch_kpi_pickup(hotel_id)

    col1, col2 = st.columns(2)

    with col1:
        has_prior_occ = not pace_df.empty and pace_df["prior_occupancy"].notna().any()
        title = t("chart.occ_current_vs_prior") if has_prior_occ else t("chart.forward_occ")
        c = chart_wrapper(title, height=400)
        with c:
            if pace_df.empty:
                st.info(t("msg.not_enough_forward"))
            elif has_prior_occ:
                df_melt = pace_df[["business_date", "current_occupancy", "prior_occupancy"]].copy()
                df_melt["business_date"] = df_melt["business_date"].astype(str)
                df_melt = df_melt.melt(
                    id_vars="business_date",
                    value_vars=["current_occupancy", "prior_occupancy"],
                    var_name="period_key", value_name="occupancy"
                )
                period_labels = {"current_occupancy": t("pacing.current"),
                                 "prior_occupancy": t("pacing.prior_year")}
                df_melt["period"] = df_melt["period_key"].map(period_labels)
                st.altair_chart(
                    alt.Chart(df_melt).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=alt.X("business_date:T", title=t("axis.date")),
                        y=alt.Y("occupancy:Q", title=t("axis.occupancy"), axis=alt.Axis(format="%")),
                        color=alt.Color("period_key:N",
                            scale=alt.Scale(domain=["current_occupancy", "prior_occupancy"],
                                            range=[C["primary"], C["gray"]]),
                            legend=alt.Legend(title=t("pacing.period")),
                            sort=None),
                        xOffset="period_key:N",
                        tooltip=[alt.Tooltip("business_date:T", title=t("axis.date")),
                                 alt.Tooltip("period:N", title=t("pacing.period")),
                                 alt.Tooltip("occupancy:Q", format=".1%", title=t("axis.occupancy"))],
                    ).properties(height=320),
                    use_container_width=True,
                )
            else:
                # No prior year data — show current OTB only as area chart
                occ_df = pace_df[["business_date", "current_occupancy"]].copy()
                occ_df["business_date"] = occ_df["business_date"].astype(str)
                area = alt.Chart(occ_df).mark_area(
                    color=C["primary"], opacity=0.25, line={"color": C["primary"], "strokeWidth": 2}
                ).encode(
                    x=alt.X("business_date:T", title=t("axis.date")),
                    y=alt.Y("current_occupancy:Q", title=t("pacing.occ_otb"),
                            axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
                    tooltip=[alt.Tooltip("business_date:T", title=t("axis.date")),
                             alt.Tooltip("current_occupancy:Q", format=".1%", title=t("pacing.otb_occupancy"))],
                ).properties(height=300)
                st.altair_chart(area, use_container_width=True)
                st.caption(t("msg.prior_year_na"))

    with col2:
        c = chart_wrapper(t("chart.pace_vs_prior"), height=400)
        with c:
            if pace_df.empty:
                st.info(t("msg.not_enough_forward"))
            else:
                pace_cols = ["occupancy_pace_pct", "adr_pace_pct", "revpar_pace_pct", "revenue_pace_pct"]
                has_prior = pace_df[pace_cols].notna().any().any()
                if not has_prior:
                    st.info(t("msg.prior_year_na_long"))
                else:
                    metric_defs = [
                        ("occupancy", "occupancy_pace_pct", t("pacing.metric_occupancy")),
                        ("adr", "adr_pace_pct", t("pacing.metric_adr")),
                        ("revpar", "revpar_pace_pct", t("pacing.metric_revpar")),
                        ("revenue", "revenue_pace_pct", t("pacing.metric_revenue")),
                    ]
                    summary = pd.DataFrame({
                        "metric_key": [m[0] for m in metric_defs],
                        "Metric": [m[2] for m in metric_defs],
                        "Pace": [pace_df[m[1]].mean() for m in metric_defs],
                    }).dropna(subset=["Pace"])
                    summary["Status"] = summary["Pace"].apply(lambda v: "ahead" if v >= 0 else "behind")
                    summary["status_label"] = summary["Status"].map(
                        {"ahead": t("pacing.ahead"), "behind": t("pacing.behind")})
                    st.altair_chart(
                        alt.Chart(summary).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
                            y=alt.Y("metric_key:N", sort=["revenue", "revpar", "adr", "occupancy"], title=None),
                            x=alt.X("Pace:Q", title=t("pacing.pace_pct_axis"), axis=alt.Axis(format="+.0f")),
                            color=alt.Color("Status:N",
                                scale=alt.Scale(domain=["ahead", "behind"], range=[C["positive"], C["negative"]]),
                                legend=None),
                            tooltip=[alt.Tooltip("Metric:N"), alt.Tooltip("Pace:Q", format="+.1f", title=t("pacing.pace_pct"))],
                        ).properties(height=200),
                        use_container_width=True,
                    )

    st.divider()

    c = chart_wrapper(t("chart.pickup"), height=300)
    with c:
        if pickup_df.empty:
            st.info(t("msg.no_future_res"))
        else:
            col_window = t("pacing.window_days")
            col_rooms = t("pacing.rooms")
            col_revenue = t("pacing.pickup_revenue")
            pickup_renamed = pickup_df.rename(columns={
                "window_days": col_window,
                "pickup_rooms": col_rooms,
                "pickup_revenue": col_revenue,
            })
            col_chart, col_table = st.columns([3, 2])
            with col_chart:
                st.altair_chart(
                    alt.Chart(pickup_renamed).mark_bar(
                        color=C["primary"], cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X(f"{col_window}:O", title=t("pacing.window_days")),
                        y=alt.Y(f"{col_rooms}:Q", title=t("pacing.room_nights_axis")),
                        tooltip=[col_window, col_rooms,
                                 alt.Tooltip(f"{col_revenue}:Q", format=",.0f")],
                    ).properties(height=220),
                    use_container_width=True,
                )
            with col_table:
                pickup_renamed[col_revenue] = pickup_renamed[col_revenue].apply(
                    lambda v: f"₫{v/1_000_000:.1f}M" if v >= 1_000_000 else f"₫{v:,.0f}"
                )
                st.dataframe(
                    pickup_renamed, use_container_width=True, hide_index=True,
                    column_config={
                        col_window: st.column_config.TextColumn(width="small"),
                        col_rooms: st.column_config.NumberColumn(format="%d"),
                    }
                )
