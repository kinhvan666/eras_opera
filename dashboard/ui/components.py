import streamlit as st


def _delta_html(current, prior, fmt, higher_is_better=True):
    if prior is None or current is None or prior == 0:
        return ""
    pct = (current - prior) / abs(prior) * 100
    positive = pct >= 0 if higher_is_better else pct < 0
    color = "var(--kpi-positive)" if positive else "var(--kpi-negative)"
    arrow = "↑" if pct >= 0 else "↓"
    return f'<span style="color:{color};font-size:12px;">{arrow} {abs(pct):.1f}%</span>'


def kpi_card(label, value, current=None, prior=None, fmt="{:.1f}", badge=None, higher_is_better=True):
    badge_html = '<span class="kpi-badge-est">EST</span>' if badge else ""
    delta_html = _delta_html(current, prior, fmt, higher_is_better)
    st.markdown(
        f"""
        <div class="kpi-card">
            <div style="color:var(--text-secondary);font-size:14px;">{label}{badge_html}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_wrapper(title, height=350):
    st.markdown(f"**{title}**")
    return st.container(border=True)
