import streamlit as st

from ui.i18n import t


def _delta_html(current, prior, fmt, higher_is_better=True):
    # Ẩn badge khi kỳ trước không có dữ liệu (None / 0 / NaN) — không so sánh giả
    if prior is None or current is None or prior == 0:
        return ""
    if prior != prior or current != current:  # NaN check
        return ""
    pct = (current - prior) / abs(prior) * 100
    positive = pct >= 0 if higher_is_better else pct < 0
    
    # Modern Badge Capsule design (uses CSS vars to adapt to theme)
    bg_color = "color-mix(in srgb, var(--kpi-positive) 15%, transparent)" if positive else "color-mix(in srgb, var(--kpi-negative) 15%, transparent)"
    text_color = "var(--kpi-positive)" if positive else "var(--kpi-negative)"
    arrow = "↑" if pct >= 0 else "↓"
    
    label = t("kpi.delta_label")
    return f'<div style="margin-top: 8px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap;"><span style="background-color:{bg_color}; color:{text_color}; font-size:12px; font-weight:600; padding:2px 8px; border-radius:100px; display:inline-flex; align-items:center; gap:2px; white-space:nowrap;">{arrow} {abs(pct):.1f}%</span><span style="color:#94A3B8; font-size:11px; white-space:nowrap;">{label}</span></div>'


def kpi_card(label, value, current=None, prior=None, fmt="{:.1f}", badge=None, higher_is_better=True):
    badge_html = f'<span class="kpi-badge-est">EST</span>' if badge else ""
    delta_html = _delta_html(current, prior, fmt, higher_is_better)
    
    st.markdown(
        f'<div class="kpi-card">'
        f'<div style="color:var(--text-secondary);font-size:14px;font-weight:500;margin-bottom:4px;">{label}{badge_html}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def chart_wrapper(title, height=350):
    st.markdown(f"**{title}**")
    return st.container(height=height, border=True)
