import base64
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from config.settings import DEFAULT_DATE_RANGE_DAYS


def fmt_vnd(val):
    if val is None:
        return "—"
    if abs(val) >= 1_000_000_000:
        return f"₫{val/1_000_000_000:.2f} Tỷ"
    if abs(val) >= 1_000_000:
        return f"₫{val/1_000_000:.1f} Tr"
    if abs(val) >= 1_000:
        return f"₫{val/1_000:.0f}K"
    return f"₫{val:,.0f}"
from data.repository import (
    fetch_kpi_summary,
    fetch_properties,
    fetch_revenue_actual_summary,
    fetch_adr_revpar_actual_summary,
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

# Row 1: Branding
st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:12px 0 8px 0">
  <img src="data:image/png;base64,{logo_b64}" style="height:44px;width:auto">
  <span style="font-size:22px;font-weight:700;color:#1E40AF;letter-spacing:-0.3px">PMS Dashboard</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# Row 2: Filters — left-aligned
today = date.today()
if "start_date" not in st.session_state:
    st.session_state["start_date"] = today - timedelta(days=DEFAULT_DATE_RANGE_DAYS)
if "end_date" not in st.session_state:
    st.session_state["end_date"] = today

p0, p1, p2, p3, _ = st.columns([0.7, 0.7, 0.7, 0.7, 6])
with p0:
    if st.button("30D", use_container_width=True):
        st.session_state["start_date"] = today - timedelta(days=30)
        st.session_state["end_date"] = today
with p1:
    if st.button("90D", use_container_width=True):
        st.session_state["start_date"] = today - timedelta(days=90)
        st.session_state["end_date"] = today
with p2:
    if st.button("MTD", use_container_width=True):
        st.session_state["start_date"] = today.replace(day=1)
        st.session_state["end_date"] = today
with p3:
    if st.button("YTD", use_container_width=True):
        st.session_state["start_date"] = today.replace(month=1, day=1)
        st.session_state["end_date"] = today

c_prop, c_from, c_to, c_refresh, _ = st.columns([3, 1.5, 1.5, 0.6, 2])

try:
    props_df = fetch_properties()
    prop_map = {"All Properties": None}
    for _, row in props_df.iterrows():
        label = row["hotel_name"] or row["hotel_id"]
        prop_map[label] = row["hotel_id"]
except Exception as e:
    prop_map = {"All Properties": None}
    st.warning(f"Could not load properties: {e}")

with c_prop:
    property_label = st.selectbox("Property", list(prop_map.keys()))
with c_from:
    start_date = st.date_input("From", value=st.session_state["start_date"], key="from_input")
    st.session_state["start_date"] = start_date
with c_to:
    end_date = st.date_input("To", value=st.session_state["end_date"], key="to_input")
    st.session_state["end_date"] = end_date
with c_refresh:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    if st.button("↻", help="Refresh data"):
        st.cache_data.clear()

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
