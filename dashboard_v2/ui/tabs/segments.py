import re

import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_kpi_daily_segmented
from ui.components import chart_wrapper
from ui.i18n import t, t_code
from ui.theme import chart_colors


def _segment_hbar(df, code_col, val_col, x_title, y_title, top_n=None):
    C = chart_colors()
    agg = df.groupby(code_col, as_index=False)[val_col].sum()
    agg = agg.sort_values(val_col, ascending=False).reset_index(drop=True)
    
    if top_n and len(agg) > top_n:
        top_df = agg.iloc[:top_n].copy()
        other_val = agg.iloc[top_n:][val_col].sum()
        if other_val > 0:
            # Sentinel không trùng mã OPERA thật (OTH là market code có thật trong dữ liệu)
            other_row = {code_col: "__OTHER__", val_col: other_val}
            agg = pd.concat([top_df, pd.DataFrame([other_row])], ignore_index=True)
        else:
            agg = top_df

    agg = agg.sort_values(val_col, ascending=False).reset_index(drop=True)
    agg["_rank"] = agg.index + 1
    
    total_nights = agg[val_col].sum()
    agg["_share"] = agg[val_col] / total_nights if total_nights > 0 else 0
    
    def get_desc(code):
        if code == "__OTHER__":
            return t("seg.other")
        return t_code(code_col, code)
    
    def axis_label(desc):
        # MAPS tiếng Việt lưu dạng "Tên EN (Tên VI)" — trên trục chỉ hiện phần
        # theo ngôn ngữ đang chọn cho gọn; tên đầy đủ vẫn nằm trong tooltip.
        if st.session_state.get("lang", "vi") == "vi":
            m = re.search(r"\(([^()]+)\)\s*$", desc)
            if m:
                return m.group(1)
        return desc

    agg["_desc"] = agg[code_col].apply(get_desc)
    agg["_axis_label"] = agg["_desc"].apply(axis_label)
    agg["_label"] = agg.apply(lambda r: f"{int(r[val_col]):,} ({r['_share']:.0%})", axis=1)
    
    bars = alt.Chart(agg).mark_bar(
        color=C["primary"],
        cornerRadiusTopRight=3,
        cornerRadiusBottomRight=3
    ).encode(
        y=alt.Y("_axis_label:N", sort="-x", title=y_title, axis=alt.Axis(labelLimit=230, labelColor=C["text_label"], titleColor=C["text_label"])),
        x=alt.X(f"{val_col}:Q", title=x_title, axis=alt.Axis(grid=True, tickCount=5, gridOpacity=0.15, labelColor=C["text_label"], titleColor=C["text_label"])),
        opacity=alt.value(1.0),
        tooltip=[
            alt.Tooltip(f"{code_col}:N", title="Mã / Code"),
            alt.Tooltip("_desc:N", title=y_title),
            alt.Tooltip(f"{val_col}:Q", format=",.0f", title=x_title),
            alt.Tooltip("_share:Q", format=".1%", title="Tỷ lệ / Share"),
        ]
    )
    
    labels = alt.Chart(agg).mark_text(
        align="left",
        dx=5,
        fontSize=11,
        fontWeight=700
    ).encode(
        y=alt.Y("_axis_label:N", sort="-x"),
        x=alt.X(f"{val_col}:Q"),
        color=alt.value(C["text_label"]),
        text=alt.Text("_label:N")
    )
    
    return alt.layer(bars, labels).resolve_scale(color='independent').properties(height=280)


def draw(start_date, end_date, hotel_id=None):
    market_df  = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "market_code")
    source_df  = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "source_of_business")
    room_df    = fetch_kpi_daily_segmented(start_date, end_date, hotel_id, "room_type")

    col1, col2 = st.columns(2)

    with col1:
        c = chart_wrapper(t("chart.seg_by_market"), height=350)
        with c:
            if market_df.empty:
                st.info(t("msg.no_market"))
            else:
                chart = _segment_hbar(
                    market_df, "market_code", "room_nights",
                    t("axis.room_nights"), t("axis.segment"), top_n=8
                )
                st.altair_chart(chart, use_container_width=True)

    with col2:
        c = chart_wrapper(t("chart.seg_by_source"), height=350)
        with c:
            if source_df.empty:
                st.info(t("msg.no_source"))
            else:
                chart = _segment_hbar(
                    source_df, "source_of_business", "room_nights",
                    t("axis.room_nights"), t("axis.source")
                )
                st.altair_chart(chart, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        c = chart_wrapper(t("chart.seg_by_roomtype"), height=350)
        with c:
            if room_df.empty:
                st.info(t("msg.no_roomtype"))
            else:
                chart = _segment_hbar(
                    room_df, "room_type", "room_nights",
                    t("axis.room_nights"), t("axis.room_type")
                )
                st.altair_chart(chart, use_container_width=True)
