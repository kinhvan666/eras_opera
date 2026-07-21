import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily_segmented
from ui.components import chart_wrapper
from ui.i18n import t

BAR_COLOR = "#1D4ED8"


def draw(start_date, end_date, hotel_id=None):
    market_df  = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "market_code")
    source_df  = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "source_of_business")
    rate_df    = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "rate_plan_code")
    room_df    = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "room_type")

    col1, col2 = st.columns(2)

    with col1:
        c = chart_wrapper(t("chart.roomnights_by_market"), height=350)
        with c:
            if market_df.empty:
                st.info(t("msg.no_market"))
            else:
                agg = market_df.sort_values("room_nights", ascending=False)
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X("market_code:N", sort="-y", title=t("axis.market")),
                        y=alt.Y("room_nights:Q", title=t("axis.room_nights")),
                        tooltip=[alt.Tooltip("market_code:N"), alt.Tooltip("room_nights:Q", title=t("axis.room_nights"))],
                    ).properties(height=280),
                    use_container_width=True,
                )

    with col2:
        c = chart_wrapper(t("chart.roomnights_by_source"), height=350)
        with c:
            if source_df.empty:
                st.info(t("msg.no_source"))
            else:
                agg = source_df.sort_values("room_nights")
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopRight=3, cornerRadiusBottomRight=3
                    ).encode(
                        y=alt.Y("source_of_business:N", sort="-x", title=t("axis.source")),
                        x=alt.X("room_nights:Q", title=t("axis.room_nights")),
                        tooltip=[alt.Tooltip("source_of_business:N"), alt.Tooltip("room_nights:Q", title=t("axis.room_nights"))],
                    ).properties(height=280),
                    use_container_width=True,
                )

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        c = chart_wrapper(t("chart.roomnights_by_rateplan"), height=350)
        with c:
            if rate_df.empty:
                st.info(t("msg.no_rateplan"))
            else:
                agg = rate_df.sort_values("room_nights", ascending=False)
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopLeft=3, cornerRadiusTopRight=3
                    ).encode(
                        x=alt.X("rate_plan_code:N", sort="-y", title=t("axis.rate_plan")),
                        y=alt.Y("room_nights:Q", title=t("axis.room_nights")),
                        tooltip=[alt.Tooltip("rate_plan_code:N"), alt.Tooltip("room_nights:Q", title=t("axis.room_nights"))],
                    ).properties(height=280),
                    use_container_width=True,
                )

    with col4:
        c = chart_wrapper(t("chart.roomnights_by_roomtype"), height=350)
        with c:
            if room_df.empty:
                st.info(t("msg.no_roomtype"))
            else:
                agg = room_df.sort_values("room_nights", ascending=False)
                st.altair_chart(
                    alt.Chart(agg).mark_bar(
                        color=BAR_COLOR, cornerRadiusTopRight=3, cornerRadiusBottomRight=3
                    ).encode(
                        y=alt.Y("room_type:N", sort="-x", title=t("axis.room_type")),
                        x=alt.X("room_nights:Q", title=t("axis.room_nights")),
                        tooltip=[alt.Tooltip("room_type:N"), alt.Tooltip("room_nights:Q", title=t("axis.room_nights"))],
                    ).properties(height=280),
                    use_container_width=True,
                )
