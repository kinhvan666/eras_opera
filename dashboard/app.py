import base64
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from config.settings import DEFAULT_DATE_RANGE_DAYS


def fmt_vnd(val):
    if val is None:
        return "—"
    if abs(val) >= 1_000_000_000:
        return f"₫{val/1_000_000_000:.2f}B"
    if abs(val) >= 1_000_000:
        return f"₫{val/1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"₫{val/1_000:.0f}K"
    return f"₫{val:,.0f}"
from data.repository import (
    fetch_kpi_summary,
    fetch_properties,
    fetch_revenue_actual_summary,
    fetch_adr_revpar_actual_summary,
    fetch_data_as_of,
)
from ui.components import kpi_card
from ui.tabs.revenue import draw as draw_revenue
from ui.tabs.trends import draw as draw_trends
from ui.tabs.segments import draw as draw_segments
from ui.tabs.pacing import draw as draw_pacing

st.set_page_config(page_title="PMS Dashboard", layout="wide")

theme_css = Path(__file__).parent / "styles" / "theme.css"
st.markdown(f"<style>{theme_css.read_text()}</style>", unsafe_allow_html=True)

logo_path = Path(__file__).parent / "logo.png"
logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

# Handle refresh via query param (triggered by HTML button below)
if "_refresh" in st.query_params:
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

try:
    as_of = fetch_data_as_of()
    as_of_str = as_of.strftime("%d %b %Y") if as_of else "N/A"
except Exception:
    as_of_str = "N/A"

# Row 1: Branding + refresh — pure HTML for full layout control
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:flex-start;padding:12px 0 8px 0">
  <div style="display:flex;align-items:center;gap:12px">
    <img src="data:image/png;base64,{logo_b64}" style="height:44px;width:auto">
    <span style="font-size:22px;font-weight:700;color:#1E40AF;letter-spacing:-0.3px">PMS Dashboard</span>
  </div>
  <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
    <a href="?_refresh=1" target="_self" style="display:inline-block;padding:4px 12px;border:1px solid #DEE2E6;border-radius:6px;background:#fff;color:#374151;font-size:16px;text-decoration:none;line-height:1.5" title="Tải lại dữ liệu mới nhất">↻</a>
    <span style="font-size:11px;color:#9CA3AF;font-style:italic">Data as of {as_of_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# Row 2: Filters
today = date.today()

def _set_preset(start):
    st.session_state["from_input"] = start
    st.session_state["to_input"] = date.today()

try:
    props_df = fetch_properties()
    prop_map = {"All Properties": None}
    for _, row in props_df.iterrows():
        label = row["hotel_name"] or row["hotel_id"]
        prop_map[label] = row["hotel_id"]
except Exception as e:
    prop_map = {"All Properties": None}
    st.warning(f"Could not load properties: {e}")

c_prop, c_from, c_to, c_30, c_90, c_mtd, c_ytd = st.columns(
    [2.5, 1.5, 1.5, 0.7, 0.7, 0.75, 0.75]
)
with c_prop:
    property_label = st.selectbox("Property", list(prop_map.keys()))
with c_from:
    start_date = st.date_input("From", value=today - timedelta(days=DEFAULT_DATE_RANGE_DAYS), key="from_input")
with c_to:
    end_date = st.date_input("To", value=today, key="to_input")
with c_30:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button("30D", on_click=_set_preset, args=(today - timedelta(days=30),), use_container_width=True)
with c_90:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button("90D", on_click=_set_preset, args=(today - timedelta(days=90),), use_container_width=True)
with c_mtd:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button("MTD", on_click=_set_preset, args=(today.replace(day=1),), use_container_width=True)
with c_ytd:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button("YTD", on_click=_set_preset, args=(today.replace(month=1, day=1),), use_container_width=True)

hotel_id = prop_map[property_label]

try:
    current, prior = fetch_kpi_summary(start_date, end_date, hotel_id)
except Exception as e:
    current, prior = None, None
    st.error(f"Could not load KPIs: {e}")

try:
    actual_revenue, prior_actual_revenue = fetch_revenue_actual_summary(start_date, end_date, hotel_id)
except Exception:
    actual_revenue, prior_actual_revenue = None, None

try:
    actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar = \
        fetch_adr_revpar_actual_summary(start_date, end_date, hotel_id)
except Exception:
    actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar = None, None, None, None

if current is None:
    st.info("No reservation data in the selected range.")
else:
    def g(d, k):
        return d.get(k) if d else None

    row1 = st.columns(5)
    with row1[0]:
        kpi_card("Revenue", fmt_vnd(actual_revenue), actual_revenue, prior_actual_revenue)
    with row1[1]:
        kpi_card("Occupancy", f"{current['occupancy'] * 100:.1f}%", current["occupancy"], g(prior, "occupancy"))
    with row1[2]:
        kpi_card("ADR", fmt_vnd(actual_adr), actual_adr, prior_actual_adr)
    with row1[3]:
        kpi_card("RevPAR", fmt_vnd(actual_revpar), actual_revpar, prior_actual_revpar)
    with row1[4]:
        kpi_card("Reservations", f"{current['reservations']:,.0f}", current["reservations"], g(prior, "reservations"))

    row2 = st.columns(5)
    with row2[0]:
        kpi_card("Room Nights", f"{current['room_nights']:,.0f}", current["room_nights"], g(prior, "room_nights"))
    with row2[1]:
        kpi_card("Lead Time", f"{current['avg_lead_time']:.1f}d", current["avg_lead_time"], g(prior, "avg_lead_time"), higher_is_better=False)
    with row2[2]:
        kpi_card("Canc. Rate", f"{current['cancellation_rate'] * 100:.1f}%", current["cancellation_rate"], g(prior, "cancellation_rate"), higher_is_better=False)

# Analytical tabs
tab_revenue, tab_trends, tab_segments, tab_pacing = st.tabs(["Revenue", "Trends", "Segments", "Pacing"])
with tab_revenue:
    draw_revenue(start_date, end_date, hotel_id)
with tab_trends:
    draw_trends(start_date, end_date, hotel_id)
with tab_segments:
    draw_segments(start_date, end_date, hotel_id)
with tab_pacing:
    draw_pacing(start_date, end_date, hotel_id)
