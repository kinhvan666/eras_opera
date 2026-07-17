from datetime import date, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from data.repository import fetch_kpi_pacing, fetch_kpi_pickup
from ui.components import chart_wrapper

BLUE  = "#0B5ED7"
GREEN = "#157347"
RED   = "#DC3545"
GRAY  = "#ADB5BD"


def draw(start_date, end_date, hotel_id=None):
    # Pacing always looks forward — ignore the dashboard's historical date filter
    today = date.today()
    pace_start = today
    pace_end = today + timedelta(days=90)

    pace_df = fetch_kpi_pacing(pace_start, pace_end, hotel_id)
    pickup_df = fetch_kpi_pickup(hotel_id)

    col1, col2 = st.columns(2)

    with col1:
        has_prior_occ = not pace_df.empty and pace_df["prior_occupancy"].notna().any()
        title = "Occupancy: Current vs Prior Year" if has_prior_occ else "Forward Occupancy (On the Books)"
        c = chart_wrapper(title, height=400)
        with c:
            if pace_df.empty:
                st.info("Not enough forward-looking data.")
            elif has_prior_occ:
                df_melt = pace_df[["business_date", "current_occupancy", "prior_occupancy"]].copy()
                df_melt["business_date"] = df_melt["business_date"].astype(str)
                df_melt = df_melt.melt(
                    id_vars="business_date",
                    value_vars=["current_occupancy", "prior_occupancy"],
                    var_name="period", value_name="occupancy"
                )
                df_melt["period"] = df_melt["period"].map({
                    "current_occupancy": "Current",
                    "prior_occupancy": "Prior Year"
                })
                st.altair_chart(
                    alt.Chart(df_melt).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                        x=alt.X("business_date:T", title="Date"),
                        y=alt.Y("occupancy:Q", title="Occupancy", axis=alt.Axis(format="%")),
                        color=alt.Color("period:N",
                            scale=alt.Scale(domain=["Current", "Prior Year"], range=[BLUE, GRAY]),
                            legend=alt.Legend(title="Period")),
                        xOffset="period:N",
                        tooltip=[alt.Tooltip("business_date:T", title="Date"),
                                 alt.Tooltip("period:N", title="Period"),
                                 alt.Tooltip("occupancy:Q", format=".1%", title="Occupancy")],
                    ).properties(height=320),
                    use_container_width=True,
                )
            else:
                # No prior year data — show current OTB only as area chart
                occ_df = pace_df[["business_date", "current_occupancy"]].copy()
                occ_df["business_date"] = occ_df["business_date"].astype(str)
                area = alt.Chart(occ_df).mark_area(
                    color=BLUE, opacity=0.25, line={"color": BLUE, "strokeWidth": 2}
                ).encode(
                    x=alt.X("business_date:T", title="Date"),
                    y=alt.Y("current_occupancy:Q", title="Occupancy (OTB)",
                            axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
                    tooltip=[alt.Tooltip("business_date:T", title="Date"),
                             alt.Tooltip("current_occupancy:Q", format=".1%", title="OTB Occupancy")],
                ).properties(height=300)
                st.altair_chart(area, use_container_width=True)
                st.caption("Prior year (2025) data not yet available for comparison.")

    with col2:
        c = chart_wrapper("Pace % vs Prior Year", height=400)
        with c:
            if pace_df.empty:
                st.info("Not enough forward-looking data.")
            else:
                pace_cols = ["occupancy_pace_pct", "adr_pace_pct", "revpar_pace_pct", "revenue_pace_pct"]
                has_prior = pace_df[pace_cols].notna().any().any()
                if not has_prior:
                    st.info(
                        "Prior year (2025) data not available — pace comparison requires "
                        "historical data from the same period last year. "
                        "This will populate once the system has been running for a full year."
                    )
                else:
                    summary = pd.DataFrame({
                        "Metric": ["Occupancy", "ADR", "RevPAR", "Revenue"],
                        "Pace": [
                            pace_df["occupancy_pace_pct"].mean(),
                            pace_df["adr_pace_pct"].mean(),
                            pace_df["revpar_pace_pct"].mean(),
                            pace_df["revenue_pace_pct"].mean(),
                        ]
                    }).dropna(subset=["Pace"])
                    summary["Status"] = summary["Pace"].apply(lambda v: "Ahead" if v >= 0 else "Behind")
                    st.altair_chart(
                        alt.Chart(summary).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
                            y=alt.Y("Metric:N", sort=["Revenue", "RevPAR", "ADR", "Occupancy"], title=None),
                            x=alt.X("Pace:Q", title="Pace vs Prior Year (%)", axis=alt.Axis(format="+.0f")),
                            color=alt.Color("Status:N",
                                scale=alt.Scale(domain=["Ahead", "Behind"], range=[GREEN, RED]),
                                legend=None),
                            tooltip=[alt.Tooltip("Metric:N"), alt.Tooltip("Pace:Q", format="+.1f", title="Pace %")],
                        ).properties(height=200),
                        use_container_width=True,
                    )

    st.divider()

    c = chart_wrapper("Pickup Analysis (7 / 30 / 90 Days)", height=300)
    with c:
        if pickup_df.empty:
            st.info("No future reservations for pickup analysis.")
        else:
            pickup_renamed = pickup_df.rename(columns={
                "window_days": "Window (days)",
                "pickup_rooms": "Rooms",
                "pickup_revenue": "Revenue (₫)"
            })
            col_chart, col_table = st.columns([3, 2])
            with col_chart:
                st.altair_chart(
                    alt.Chart(pickup_renamed).mark_bar(
                        color=BLUE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X("Window (days):O", title="Pickup Window (days)"),
                        y=alt.Y("Rooms:Q", title="Rooms Picked Up"),
                        tooltip=["Window (days)", "Rooms",
                                 alt.Tooltip("Revenue (₫):Q", format=",.0f")],
                    ).properties(height=220),
                    use_container_width=True,
                )
            with col_table:
                pickup_renamed["Revenue (₫)"] = pickup_renamed["Revenue (₫)"].apply(
                    lambda v: f"₫{v/1_000_000:.1f}M" if v >= 1_000_000 else f"₫{v:,.0f}"
                )
                st.dataframe(
                    pickup_renamed, use_container_width=True, hide_index=True,
                    column_config={
                        "Window (days)": st.column_config.TextColumn(width="small"),
                        "Rooms": st.column_config.NumberColumn(format="%d"),
                    }
                )
