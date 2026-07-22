from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from data.repository import fetch_kpi_pacing, fetch_kpi_pickup, fetch_pickup_daily
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
                        x=alt.X("business_date:T", title=t("axis.date"), axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                        y=alt.Y("occupancy:Q", title=t("axis.occupancy"), axis=alt.Axis(format="%", labelColor=C["text_label"], titleColor=C["text_label"])),
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
                    x=alt.X("business_date:T", title=t("axis.date"), axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                    y=alt.Y("current_occupancy:Q", title=t("pacing.occ_otb"),
                            axis=alt.Axis(format=".0%", labelColor=C["text_label"], titleColor=C["text_label"]), scale=alt.Scale(domain=[0, 1])),
                    tooltip=[alt.Tooltip("business_date:T", title=t("axis.date")),
                             alt.Tooltip("current_occupancy:Q", format=".1%", title=t("pacing.otb_occupancy"))],
                ).properties(height=300)
                st.altair_chart(area, use_container_width=True)

    with col2:
        pace_cols = ["occupancy_pace_pct", "adr_pace_pct", "revpar_pace_pct", "revenue_pace_pct"]
        has_prior = not pace_df.empty and pace_df[pace_cols].notna().any().any()
        wrapper_title = t("chart.pace_vs_prior") if pace_df.empty or has_prior else t("chart.pickup_daily")
        c = chart_wrapper(wrapper_title, height=400)
        with c:
            if pace_df.empty:
                st.info(t("msg.not_enough_forward"))
            else:
                if not has_prior:
                    pickup_d = fetch_pickup_daily(hotel_id, 30)
                    if pickup_d.empty:
                        st.info(t("msg.prior_year_na_long"))
                    else:
                        st.altair_chart(
                            alt.Chart(pickup_d).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                                x=alt.X("booking_date:T", title=t("axis.date"), axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                                y=alt.Y("room_nights:Q", title=t("pacing.rooms"), axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                                color=alt.value(C["primary"]),
                                tooltip=[
                                    alt.Tooltip("booking_date:T", title=t("axis.date")),
                                    alt.Tooltip("room_nights:Q", title=t("pacing.rooms")),
                                    alt.Tooltip("est_revenue:Q", title=t("pacing.pickup_revenue"), format=",.0f")
                                ]
                            ).properties(height=320),
                            use_container_width=True
                        )
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
                            y=alt.Y("metric_key:N", sort=["revenue", "revpar", "adr", "occupancy"], title=None, axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                            x=alt.X("Pace:Q", title=t("pacing.pace_pct_axis"), axis=alt.Axis(format="+.0f", labelColor=C["text_label"], titleColor=C["text_label"])),
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
            w = pickup_df.set_index("window_days")
            def safe_get(idx, col):
                return w.loc[idx, col] if idx in w.index else 0
                
            buckets = pd.DataFrame({
                "bucket": [t("pacing.bucket_0_7"), t("pacing.bucket_8_30"), t("pacing.bucket_31_90")],
                "room_nights": [
                    safe_get(7, "pickup_rooms"),
                    safe_get(30, "pickup_rooms") - safe_get(7, "pickup_rooms"),
                    safe_get(90, "pickup_rooms") - safe_get(30, "pickup_rooms")
                ],
                "est_revenue": [
                    safe_get(7, "pickup_revenue"),
                    safe_get(30, "pickup_revenue") - safe_get(7, "pickup_revenue"),
                    safe_get(90, "pickup_revenue") - safe_get(30, "pickup_revenue")
                ],
            })
            
            table_df = buckets.copy()
            table_df.loc[len(table_df)] = [t("pacing.total"), safe_get(90, "pickup_rooms"), safe_get(90, "pickup_revenue")]
            
            col_window = t("pacing.window_days")
            col_rooms = t("pacing.rooms")
            col_revenue = t("pacing.pickup_revenue")
            
            table_renamed = table_df.rename(columns={
                "bucket": col_window,
                "room_nights": col_rooms,
                "est_revenue": col_revenue,
            })
            
            col_chart, col_table = st.columns([3, 2])
            with col_chart:
                st.altair_chart(
                    alt.Chart(buckets).mark_bar(
                        cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X("bucket:N", title=t("pacing.window_days"), sort=None, axis=alt.Axis(labelAngle=0, labelColor=C["text_label"], titleColor=C["text_label"])),
                        y=alt.Y("room_nights:Q", title=t("pacing.room_nights_axis"), axis=alt.Axis(labelColor=C["text_label"], titleColor=C["text_label"])),
                        color=alt.value(C["primary"]),
                        tooltip=[
                            alt.Tooltip("bucket:N", title=t("pacing.window_days")), 
                            alt.Tooltip("room_nights:Q", title=t("pacing.rooms")),
                            alt.Tooltip("est_revenue:Q", title=t("pacing.pickup_revenue"), format=",.0f")
                        ],
                    ).properties(height=220),
                    use_container_width=True,
                )
            with col_table:
                table_renamed[col_revenue] = table_renamed[col_revenue].apply(
                    lambda v: f"₫{v/1_000_000:.1f}M" if v >= 1_000_000 else f"₫{v:,.0f}"
                )
                html_rows = ""
                for idx, row in table_renamed.iterrows():
                    is_total = (idx == len(table_renamed) - 1)
                    tr_style = f"font-weight: 700; background-color: {C['band']}33;" if is_total else ""
                    border_style = f"border-bottom: 1px solid {C['gray']}33;" if not is_total else ""
                    html_rows += f'<tr style="{tr_style}">'
                    html_rows += f'<td style="padding: 12px 16px; {border_style} color: {C["text_label"]};">{row[col_window]}</td>'
                    html_rows += f'<td style="padding: 12px 16px; {border_style} text-align: right; color: {C["text_label"]};">{int(row[col_rooms]):,}</td>'
                    html_rows += f'<td style="padding: 12px 16px; {border_style} text-align: right; color: {C["text_label"]};">{row[col_revenue]}</td>'
                    html_rows += '</tr>'
                
                table_html = f'<div style="width: 100%; border: 1px solid {C["gray"]}33; border-radius: 8px; overflow: hidden; margin-top: 8px;">'
                table_html += f'<table style="width: 100%; border-collapse: collapse; font-family: inherit; font-size: 14px; margin: 0;">'
                table_html += f'<thead><tr style="background-color: {C["band"]}; border-bottom: 1px solid {C["gray"]}55;">'
                table_html += f'<th style="padding: 14px 16px; text-align: left; font-weight: 600; color: {C["text_label"]};">{col_window}</th>'
                table_html += f'<th style="padding: 14px 16px; text-align: right; font-weight: 600; color: {C["text_label"]};">{col_rooms}</th>'
                table_html += f'<th style="padding: 14px 16px; text-align: right; font-weight: 600; color: {C["text_label"]};">{col_revenue}</th>'
                table_html += '</tr></thead>'
                table_html += f'<tbody>{html_rows}</tbody>'
                table_html += '</table></div>'
                
                st.markdown(table_html, unsafe_allow_html=True)
