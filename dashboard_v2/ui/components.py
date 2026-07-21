import streamlit as st


def _delta_html(current, prior, fmt, higher_is_better=True):
    if prior is None or current is None or prior == 0:
        return ""
    pct = (current - prior) / abs(prior) * 100
    positive = pct >= 0 if higher_is_better else pct < 0
    
    # Modern Badge Capsule design for dark mode
    bg_color = "rgba(52, 211, 153, 0.15)" if positive else "rgba(248, 113, 113, 0.15)"
    text_color = "#34D399" if positive else "#F87171"
    arrow = "↑" if pct >= 0 else "↓"
    
    lang = st.session_state.get("lang", "en")
    label = "vs kỳ trước" if lang == "vi" else "vs prior period"
    
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
