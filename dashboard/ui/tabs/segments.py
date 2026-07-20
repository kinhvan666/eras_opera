import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily_segmented
from ui.components import chart_wrapper

BAR_COLOR = "#1D4ED8"


def draw(start_date, end_date, hotel_id=None):
    market_df  = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "market_code")
    source_df  = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "source_of_business")
    rate_df    = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "rate_plan_code")
    room_df    = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "room_type")

    col1, col2 = st.columns(2)

    with col1:
        c = chart_wrapper("Room Nights by Market", height=350)
        with c:
            if market_df.empty:
                st.info("No market data")
            else:
                agg = market_df.sort_values("room_nights", ascending=False)
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X("market_code:N", sort="-y", title="Market"),
                        y=alt.Y("room_nights:Q", title="Room Nights"),
                        tooltip=["market_code", "room_nights"],
                    ).properties(height=280),
                    use_container_width=True,
                )

    with col2:
        c = chart_wrapper("Room Nights by Source", height=350)
        with c:
            if source_df.empty:
                st.info("No source data")
            else:
                agg = source_df.sort_values("room_nights")
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopRight=3, cornerRadiusBottomRight=3
                    ).encode(
                        y=alt.Y("source_of_business:N", sort="-x", title="Source"),
                        x=alt.X("room_nights:Q", title="Room Nights"),
                        tooltip=["source_of_business", "room_nights"],
                    ).properties(height=280),
                    use_container_width=True,
                )

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        c = chart_wrapper("Room Nights by Rate Plan", height=350)
        with c:
            if rate_df.empty:
                st.info("No rate plan data")
            else:
                agg = rate_df.sort_values("room_nights", ascending=False)
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X("rate_plan_code:N", sort="-y", title="Rate Plan"),
                        y=alt.Y("room_nights:Q", title="Room Nights"),
                        tooltip=["rate_plan_code", "room_nights"],
                    ).properties(height=280),
                    use_container_width=True,
                )

    with col4:
        c = chart_wrapper("Room Nights by Room Type", height=350)
        with c:
            if room_df.empty:
                st.info("No room type data")
            else:
                agg = room_df.sort_values("room_nights", ascending=False)
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopRight=3, cornerRadiusBottomRight=3
                    ).encode(
                        y=alt.Y("room_type:N", sort="-x", title="Room Type"),
                        x=alt.X("room_nights:Q", title="Room Nights"),
                        tooltip=["room_type", "room_nights"],
                    ).properties(height=280),
                    use_container_width=True,
                )
