import base64
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from config.settings import DEFAULT_DATE_RANGE_DAYS
from ui.i18n import t


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
    fetch_adr_revpar_actual_summary,
    fetch_data_as_of,
)
from ui.components import kpi_card
from ui.tabs.revenue import draw as draw_revenue
from ui.tabs.trends import draw as draw_trends
from ui.tabs.segments import draw as draw_segments
from ui.tabs.pacing import draw as draw_pacing

if "lang" not in st.session_state:
    st.session_state["lang"] = "vi"

# Handle lang switch via query param
if "lang" in st.query_params:
    st.session_state["lang"] = st.query_params["lang"]
    del st.query_params["lang"]
    st.rerun()

st.set_page_config(page_title=t("app.title"), layout="wide")

theme_css = Path(__file__).parent / "styles" / "theme.css"
st.markdown(f"<style>{theme_css.read_text()}</style>", unsafe_allow_html=True)

logo_path = Path(__file__).parent / "logo.png"
logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

# Handle refresh via query param
if "_refresh" in st.query_params:
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

try:
    as_of = fetch_data_as_of()
    as_of_str = as_of.strftime("%d %b %Y") if as_of else "N/A"
except Exception:
    as_of_str = "N/A"

# Header: pure HTML flexbox — logo+title bên trái cao hơn, EN/VI/↻/data-as-of bên phải sát cạnh ngang xám
lang = st.session_state["lang"]
_btn_base = "display:inline-block;padding:5px 14px;font-size:14px;font-weight:500;text-decoration:none;cursor:pointer;border:1px solid #DEE2E6;transition:all 0.15s ease-in-out"
_active_state = "background:#1E40AF;color:#fff;border-color:#1E40AF;z-index:2;position:relative"
_inactive_state = "background:#fff;color:#374151;border-color:#DEE2E6;position:relative"

_btn_left = f"{_btn_base};border-top-left-radius:6px;border-bottom-left-radius:6px;margin-right:-1px"
_btn_middle = f"{_btn_base};border-radius:0;margin-right:-1px"
_btn_right = f"{_btn_base};border-top-right-radius:6px;border-bottom-right-radius:6px"

style_en = f"{_btn_left};{_active_state if lang == 'en' else _inactive_state}"
style_vi = f"{_btn_middle};{_active_state if lang == 'vi' else _inactive_state}"
style_refresh = f"{_btn_right};{_inactive_state}"

st.markdown(f"""
<div>
  <!-- Row 1: Logo and Brand -->
  <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0 10px 0">
    <div style="display:flex;align-items:center;gap:12px">
      <img src="data:image/png;base64,{logo_b64}" style="height:44px;width:auto">
      <span style="font-size:22px;font-weight:700;color:#1E40AF;letter-spacing:-0.3px">{t('app.title')}</span>
    </div>
  </div>
  <!-- Row 2: Buttons & Data as of, aligned to the bottom divider -->
  <div style="display:flex;justify-content:flex-end;align-items:flex-end;padding:0 0 8px 0;border-bottom:1px solid #DEE2E6;margin-bottom:16px">
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
      <div style="display:flex;align-items:center"><a href="?lang=en" target="_self" style="{style_en}">{t('lang.en')}</a><a href="?lang=vi" target="_self" style="{style_vi}">{t('lang.vi')}</a><a href="?_refresh=1" target="_self" style="{style_refresh}" title="{t('header.refresh_title')}">↻</a></div>
      <span style="font-size:11px;color:#9CA3AF;font-style:italic;white-space:nowrap">{t('header.data_as_of', date=as_of_str)}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Row 2: Filters
today = date.today()

def _set_preset(start):
    st.session_state["from_input"] = start
    st.session_state["to_input"] = date.today()

# Khởi tạo session state mặc định nếu chưa có — tránh conflict với preset buttons
if "from_input" not in st.session_state:
    st.session_state["from_input"] = today - timedelta(days=DEFAULT_DATE_RANGE_DAYS)
if "to_input" not in st.session_state:
    st.session_state["to_input"] = today

try:
    props_df = fetch_properties()
    prop_map = {t("filter.all_properties"): None}
    for _, row in props_df.iterrows():
        label = row["hotel_name"] or row["hotel_id"]
        prop_map[label] = row["hotel_id"]
except Exception as e:
    prop_map = {t("filter.all_properties"): None}
    st.warning(t("msg.load_properties_err", e=e))

c_prop, c_from, c_to, c_30, c_90, c_mtd, c_ytd = st.columns(
    [2.5, 1.5, 1.5, 0.7, 0.7, 0.75, 0.75]
)
with c_prop:
    property_label = st.selectbox(t("filter.property"), list(prop_map.keys()))
with c_from:
    start_date = st.date_input(t("filter.from"), key="from_input")
with c_to:
    end_date = st.date_input(t("filter.to"), key="to_input")
with c_30:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button(t("preset.30d"), on_click=_set_preset, args=(today - timedelta(days=30),), use_container_width=True)
with c_90:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button(t("preset.90d"), on_click=_set_preset, args=(today - timedelta(days=90),), use_container_width=True)
with c_mtd:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button(t("preset.mtd"), on_click=_set_preset, args=(today.replace(day=1),), use_container_width=True)
with c_ytd:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    st.button(t("preset.ytd"), on_click=_set_preset, args=(today.replace(month=1, day=1),), use_container_width=True)

hotel_id = prop_map[property_label]

try:
    current, prior = fetch_kpi_summary(start_date, end_date, hotel_id)
except Exception as e:
    current, prior = None, None
    st.error(t("msg.load_kpis_err", e=e))

try:
    actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar = \
        fetch_adr_revpar_actual_summary(start_date, end_date, hotel_id)
except Exception:
    actual_adr, actual_revpar, prior_actual_adr, prior_actual_revpar = None, None, None, None

if current is None:
    st.info(t("msg.no_reservation"))
else:
    def g(d, k):
        return d.get(k) if d else None

    row1 = st.columns(5)
    with row1[0]:
        kpi_card(t("kpi.revenue"), fmt_vnd(g(current, "total_revenue")), g(current, "total_revenue"), g(prior, "total_revenue"))
    with row1[1]:
        kpi_card(t("kpi.occupancy"), f"{current['occupancy'] * 100:.1f}%", current["occupancy"], g(prior, "occupancy"))
    with row1[2]:
        kpi_card(t("kpi.adr"), fmt_vnd(actual_adr), actual_adr, prior_actual_adr)
    with row1[3]:
        kpi_card(t("kpi.revpar"), fmt_vnd(actual_revpar), actual_revpar, prior_actual_revpar)
    with row1[4]:
        kpi_card(t("kpi.reservations"), f"{current['reservations']:,.0f}", current["reservations"], g(prior, "reservations"))

    row2 = st.columns(5)
    with row2[0]:
        kpi_card(t("kpi.room_nights"), f"{current['room_nights']:,.0f}", current["room_nights"], g(prior, "room_nights"))
    with row2[1]:
        kpi_card(t("kpi.lead_time"), f"{current['avg_lead_time']:.1f}d", current["avg_lead_time"], g(prior, "avg_lead_time"), higher_is_better=False)
    with row2[2]:
        kpi_card(t("kpi.cancel_rate"), f"{current['cancellation_rate'] * 100:.1f}%", current["cancellation_rate"], g(prior, "cancellation_rate"), higher_is_better=False)

# Analytical tabs
tab_revenue, tab_trends, tab_segments, tab_pacing = st.tabs(
    [t("tab.revenue"), t("tab.trends"), t("tab.segments"), t("tab.pacing")]
)
with tab_revenue:
    draw_revenue(start_date, end_date, hotel_id)
with tab_trends:
    draw_trends(start_date, end_date, hotel_id)
with tab_segments:
    draw_segments(start_date, end_date, hotel_id)
with tab_pacing:
    draw_pacing(start_date, end_date, hotel_id)
