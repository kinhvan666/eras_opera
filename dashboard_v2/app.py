import base64
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from config.settings import DEFAULT_DATE_RANGE_DAYS
from ui.i18n import t
from auth.session import require_login, logout, is_admin


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

st.set_page_config(page_title="ERAS Group Dashboard", layout="wide")

# ── Auth guard — stops here and shows login page if not authenticated ──────
user = require_login()

# ── Admin page routing via query param ──
if st.query_params.get("page") == "admin" and is_admin():
    from pages.admin import render_admin
    render_admin()
    st.stop()

from ui.theme import current_theme

def _apply_theme(mode: str):
    # Set all Streamlit theme options for complete runtime theme flipping
    if mode == "light":
        st.config.set_option("theme.base", "light")
        st.config.set_option("theme.primaryColor", "#2563EB")
        st.config.set_option("theme.backgroundColor", "#F8FAFC")
        st.config.set_option("theme.secondaryBackgroundColor", "#FFFFFF")
        st.config.set_option("theme.textColor", "#0F172A")
    else:
        st.config.set_option("theme.base", "dark")
        st.config.set_option("theme.primaryColor", "#3B82F6")
        st.config.set_option("theme.backgroundColor", "#020617")
        st.config.set_option("theme.secondaryBackgroundColor", "#0E1223")
        st.config.set_option("theme.textColor", "#F8FAFC")

if "ui_theme" not in st.session_state:
    qp = st.query_params.get("theme")
    if qp in ("light", "dark"):
        st.session_state["ui_theme"] = qp
    else:
        try:
            st.session_state["ui_theme"] = st.context.theme.type or "dark"
        except Exception:
            st.session_state["ui_theme"] = "dark"

# Re-assert mỗi rerun (chống race đa user), tối đa 1 lần rerun sửa lệch mỗi phiên
try:
    _rendered = st.context.theme.type
except Exception:
    _rendered = None
if _rendered and _rendered != st.session_state["ui_theme"] \
        and not st.session_state.get("_theme_rerun_once"):
    st.session_state["_theme_rerun_once"] = True
    _apply_theme(st.session_state["ui_theme"])
    st.rerun()
st.session_state.pop("_theme_rerun_once", None)

css = (Path(__file__).parent / "styles" / "theme.css").read_text()
if st.session_state["ui_theme"] == "light":
    css += (Path(__file__).parent / "styles" / "theme-light.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Patch st.altair_chart to explicitly sync with ui_theme instead of relying on buggy Streamlit native theme
_orig_altair_chart = st.altair_chart
def _patched_altair_chart(altair_chart, use_container_width=False, theme="streamlit", **kwargs):
    import altair as alt
    is_light = st.session_state.get("ui_theme", "light") == "light"
    text_color = "#0F172A" if is_light else "#F8FAFC"
    axis_color = "#E2E8F0" if is_light else "#334155"
    
    altair_chart = altair_chart.configure(
        background="transparent",
        title=alt.TitleConfig(color=text_color),
        axis=alt.AxisConfig(
            labelColor=text_color,
            titleColor=text_color,
            domainColor=axis_color,
            gridColor=axis_color,
            tickColor=axis_color
        ),
        legend=alt.LegendConfig(
            labelColor=text_color,
            titleColor=text_color
        ),
        view=alt.ViewConfig(strokeOpacity=0)
    )
    return _orig_altair_chart(altair_chart, use_container_width=use_container_width, theme=None, **kwargs)

st.altair_chart = _patched_altair_chart

logo_path = Path(__file__).parent / "logo.png"
logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

# Handle refresh via query param
if "refresh" in st.query_params or "_refresh" in st.query_params:
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

if st.query_params.get("logout") == "1":
    st.query_params.clear()
    logout()

try:
    as_of = fetch_data_as_of()
    as_of_str = as_of.strftime("%d %b %Y") if as_of else "N/A"
except Exception:
    as_of_str = "N/A"

# ── Top Brand Header ──
lang = st.session_state.get("lang", "vi")
admin_link = f'<a href="?page=admin" target="_self" style="color:var(--text-secondary);font-size:12px;text-decoration:none;" title="{t("auth.admin_panel")}">{t("auth.admin_panel")}</a>' if is_admin() else ""

col_logo, col_user = st.columns([0.55, 0.45])
with col_logo:
    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:12px;padding:4px 0;">
      <img src="data:image/png;base64,{logo_b64}" style="height:42px;width:auto;">
      <span style="font-size:22px;font-weight:700;background:linear-gradient(90deg,var(--title-gradient-from) 0%,var(--title-gradient-to) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.3px;">{t("app.title")}</span>
    </div>
    ''', unsafe_allow_html=True)

with col_user:
    st.markdown(f'''
    <div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-bottom:6px;">
      <span style="color:var(--text-secondary);font-size:13px;font-weight:500;font-style:italic;">{t("header.welcome", name=user["display_name"])}</span>
      {admin_link}
    </div>
    ''', unsafe_allow_html=True)

    # Compact button group hugging the right edge
    with st.container(horizontal=True, horizontal_alignment="right", gap=None, key="hdr_btns"):
        if st.button(t("lang.en"), key="hdr_en", type="primary" if lang == "en" else "secondary"):
            st.session_state["lang"] = "en"
            st.rerun()
        if st.button(t("lang.vi"), key="hdr_vi", type="primary" if lang == "vi" else "secondary"):
            st.session_state["lang"] = "vi"
            st.rerun()
        if st.button("↻", key="hdr_rf", type="secondary", help=t("header.refresh_title")):
            st.cache_data.clear()
            st.rerun()
        if st.button("⎋", key="hdr_lo", type="secondary", help=t("auth.logout")):
            logout()
        _icon = "☀️" if st.session_state["ui_theme"] == "dark" else "🌙"
        if st.button(_icon, key="hdr_theme", type="secondary", help=t("header.theme_title")):
            new = "light" if st.session_state["ui_theme"] == "dark" else "dark"
            st.session_state["ui_theme"] = new
            st.query_params["theme"] = new
            _apply_theme(new)
            st.rerun()

    st.markdown(f'''
    <div style="text-align:right;margin-top:4px;">
      <span style="font-size:11px;color:var(--text-secondary);font-style:italic;white-space:nowrap;">{t("header.data_as_of", date=as_of_str)}</span>
    </div>
    ''', unsafe_allow_html=True)

st.markdown('<div style="border-bottom:1px solid var(--border);margin:8px 0 16px 0;"></div>', unsafe_allow_html=True)

# Row 2: Filters
today = date.today()

# Khởi tạo session state mặc định nếu chưa có — tránh conflict với preset buttons
if "from_input" not in st.session_state:
    st.session_state["from_input"] = today - timedelta(days=DEFAULT_DATE_RANGE_DAYS)
if "to_input" not in st.session_state:
    st.session_state["to_input"] = today

def _set_preset(start):
    st.session_state["from_input"] = start
    st.session_state["to_input"] = date.today()

try:
    props_df = fetch_properties()
    # Filter properties theo user permissions
    allowed = user.get("allowed_hotel_ids")  # None = all, list = specific
    if allowed is not None:
        props_df = props_df[props_df["hotel_id"].isin(allowed)]

    prop_map = {}
    # Chỉ show "All Properties" nếu user có quyền nhiều hơn 1 property
    if len(props_df) > 1:
        prop_map[t("filter.all_properties")] = None
    for _, row in props_df.iterrows():
        label = row["hotel_name"] or row["hotel_id"]
        prop_map[label] = row["hotel_id"]
except Exception as e:
    prop_map = {t("filter.all_properties"): None}
    st.warning(t("msg.load_properties_err", e=e))

c_prop, c_from, c_to, c_30, c_90, c_mtd, c_ytd = st.columns(
    [2.0, 1.3, 1.3, 0.85, 0.85, 0.85, 0.85]
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

    # Hàng 1: Chỉ số cốt lõi kinh doanh (Core Metrics)
    row1 = st.columns(4)
    with row1[0]:
        kpi_card(t("kpi.revenue"), fmt_vnd(g(current, "total_revenue")), g(current, "total_revenue"), g(prior, "total_revenue"))
    with row1[1]:
        kpi_card(t("kpi.room_nights"), f"{current['room_nights']:,.0f}", current["room_nights"], g(prior, "room_nights"))
    with row1[2]:
        kpi_card(t("kpi.occupancy"), f"{current['occupancy'] * 100:.1f}%", current["occupancy"], g(prior, "occupancy"))
    with row1[3]:
        kpi_card(t("kpi.adr"), fmt_vnd(actual_adr), actual_adr, prior_actual_adr)

    # Hàng 2: Chỉ số hiệu suất & Quy mô (Efficiency & Volume Metrics)
    row2 = st.columns(4)
    with row2[0]:
        kpi_card(t("kpi.revpar"), fmt_vnd(actual_revpar), actual_revpar, prior_actual_revpar)
    with row2[1]:
        kpi_card(t("kpi.reservations"), f"{current['reservations']:,.0f}", current["reservations"], g(prior, "reservations"))
    with row2[2]:
        kpi_card(t("kpi.lead_time"), f"{current['avg_lead_time']:.1f} {t('kpi.lead_time_unit')}", current["avg_lead_time"], g(prior, "avg_lead_time"), higher_is_better=False)
    with row2[3]:
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
