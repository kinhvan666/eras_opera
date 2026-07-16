import altair as alt
import pandas as pd
import streamlit as st


def executive_kpi_card(label, value, delta_pct, sparkline_data, status="on_track"):
    """
    Executive KPI card with status badge and inline sparkline.

    Args:
        label: KPI name (e.g., "Revenue", "Occupancy")
        value: Formatted value string (e.g., "$1.2M", "72.3%")
        delta_pct: Percentage change vs prior period (positive/negative)
        sparkline_data: DataFrame with 'date' and 'value' columns for sparkline
        status: "on_track" | "at_risk" | "critical"
    """
    status_config = {
        "on_track": {"color": "var(--status-on-track)", "label": "On Track", "bg": "rgba(34, 197, 94, 0.15)"},
        "at_risk": {"color": "var(--status-at-risk)", "label": "At Risk", "bg": "rgba(245, 158, 11, 0.15)"},
        "critical": {"color": "var(--status-critical)", "label": "Critical", "bg": "rgba(239, 68, 68, 0.15)"}
    }

    cfg = status_config.get(status, status_config["on_track"])
    delta_color = "var(--kpi-positive)" if delta_pct >= 0 else "var(--kpi-negative)"
    arrow = "↗" if delta_pct >= 0 else "↘"

    # Build sparkline SVG
    sparkline_svg = ""
    if sparkline_data is not None and not sparkline_data.empty:
        sparkline_svg = _build_sparkline_svg(sparkline_data)

    st.markdown(f"""
    <div class="exec-kpi-card">
        <div class="exec-kpi-header">
            <span class="exec-kpi-label">{label}</span>
            <span class="exec-kpi-status" style="background:{cfg['bg']}; color:{cfg['color']};">
                ● {cfg['label']}
            </span>
        </div>
        <div class="exec-kpi-value" style="font-family:var(--font-mono);font-size:var(--kpi-value-size);">
            {value}
        </div>
        <div class="exec-kpi-delta" style="color:{delta_color};">
            {arrow} {abs(delta_pct):.1f}% vs prior
        </div>
        <div class="exec-kpi-sparkline" style="height:var(--sparkline-height);">
            {sparkline_svg}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _build_sparkline_svg(df: pd.DataFrame) -> str:
    """Build inline SVG sparkline from DataFrame with 'date' and 'value' columns."""
    if df.empty or len(df) < 2:
        return ""

    values = df['value'].values
    min_val, max_val = values.min(), values.max()
    if min_val == max_val:
        return ""

    width = 120
    height = 28
    padding = 2

    # Normalize values to 0-1
    normalized = [(v - min_val) / (max_val - min_val) for v in values]

    # Build path
    points = []
    for i, norm in enumerate(normalized):
        x = padding + (i / (len(normalized) - 1)) * (width - 2 * padding)
        y = height - padding - norm * (height - 2 * padding)
        points.append(f"{x},{y}")

    path = "M " + " L ".join(points)

    # Area under line
    area_points = [f"{width - padding},{height - padding}"] + [f"{p.split(',')[0]},{height - padding}" for p in reversed(points)]
    area_path = "M " + " L ".join(points) + " L " + " L ".join(area_points) + " Z"

    color = "var(--kpi-positive)" if values[-1] >= values[0] else "var(--kpi-negative)"

    # No leading newline/whitespace — keeps Streamlit HTML parser from injecting stray closing tags
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="display:block;">'
        f'<path d="{area_path}" fill="{color}" fill-opacity="0.12"/>'
        f'<path d="{path}" stroke="{color}" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


def property_portfolio_table(df: pd.DataFrame):
    """
    Render property portfolio comparison table.
    Expected columns: property_name, region, revenue, adr, occupancy, revpar, status
    """
    if df.empty:
        st.markdown("""
        <div class="exec-empty-state">
            <div class="exec-empty-state-icon">📊</div>
            <div>No property data available for selected period.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Style status column
    def style_status(status):
        config = {
            "on_track": "exec-status-on-track",
            "at_risk": "exec-status-at-risk",
            "critical": "exec-status-critical"
        }
        return config.get(status, "exec-status-on-track")

    st.markdown('<div class="exec-property-table">', unsafe_allow_html=True)

    # Header
    cols = st.columns([2.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5])
    headers = ["Property", "Region", "Revenue", "ADR", "Occupancy", "RevPAR", "Status"]
    header_html = '<div class="exec-table-header">'
    for col, header in zip(cols, headers):
        with col:
            st.markdown(f'<div style="font-weight:600;text-transform:uppercase;font-size:11px;color:var(--text-muted);">{header}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Rows
    for _, row in df.iterrows():
        cols = st.columns([2.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5])
        status_class = style_status(row.get('status', 'on_track'))

        with cols[0]:
            st.markdown(f'<div class="exec-table-cell"><strong>{row.get("property_name", "")}</strong></div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f'<div class="exec-table-cell" style="color:var(--text-secondary);">{row.get("region", "")}</div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f'<div class="exec-table-cell exec-table-cell-value">{row.get("revenue", "")}</div>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f'<div class="exec-table-cell exec-table-cell-value">{row.get("adr", "")}</div>', unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f'<div class="exec-table-cell exec-table-cell-value">{row.get("occupancy", "")}</div>', unsafe_allow_html=True)
        with cols[5]:
            st.markdown(f'<div class="exec-table-cell exec-table-cell-value">{row.get("revpar", "")}</div>', unsafe_allow_html=True)
        with cols[6]:
            status_label = {"on_track": "On Track", "at_risk": "At Risk", "critical": "Critical"}.get(row.get('status', 'on_track'), "On Track")
            st.markdown(f'<span class="exec-status-badge {status_class}">{status_label}</span>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def executive_tab_bar(active_tab: str):
    """Render executive dashboard tab bar."""
    tabs = [
        ("overview", "Overview"),
        ("properties", "Properties"),
        ("budget", "Budget vs Actual"),
        ("forecast", "Forecast")
    ]

    cols = st.columns(len(tabs))
    for col, (tab_id, tab_label) in zip(cols, tabs):
        with col:
            is_active = tab_id == active_tab
            if st.button(tab_label, key=f"exec_tab_{tab_id}",
                        use_container_width=True,
                        type="primary" if is_active else "secondary"):
                st.session_state['exec_active_tab'] = tab_id
                st.rerun()


def section_title(title: str):
    """Render executive section title."""
    st.markdown(f'<div class="exec-section-title">{title}</div>', unsafe_allow_html=True)


def chart_container(fig, height=350):
    """Consistent chart container wrapper."""
    st.markdown('<div class="exec-chart-container">', unsafe_allow_html=True)
    st.altair_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)