import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from config.settings import DEFAULT_DATE_RANGE_DAYS
from executive.data.repository import (determine_status, fetch_executive_kpi_summary,
                            fetch_executive_properties, fetch_executive_kpi_daily,
                            fetch_monthly_revenue, fetch_property_portfolio,
                            fetch_sparkline_data)
from executive.ui.components import (chart_container, executive_kpi_card, executive_tab_bar,
                           property_portfolio_table, section_title)

st.set_page_config(page_title="ErasOpera Executive Dashboard", layout="wide")

# Load theme CSS
theme_css = Path(__file__).parent / "styles" / "theme.css"
st.markdown(f"<style>{theme_css.read_text()}</style>", unsafe_allow_html=True)

# Header
st.markdown("**ErasOpera Group > Executive Dashboard**")
st.title("Executive Dashboard")

# Initialize session state
if 'exec_active_tab' not in st.session_state:
    st.session_state['exec_active_tab'] = 'overview'

# Filter Bar
col_filter1, col_filter2, col_filter3, col_refresh = st.columns([2, 1, 1, 1])

with col_filter1:
    try:
        properties = fetch_executive_properties()
        prop_options = ["All Properties"] + [f"{row['hotel_id']} ({row['hotel_name'] or row['hotel_id']})" for _, row in properties.iterrows()]
    except Exception as e:
        prop_options = ["All Properties"]
        st.warning(f"Could not load properties: {e}")
    property_choice = st.selectbox("Property Group", prop_options)

with col_filter2:
    start_date = st.date_input("From", value=date.today() - timedelta(days=DEFAULT_DATE_RANGE_DAYS))

with col_filter3:
    end_date = st.date_input("To", value=date.today())

with col_refresh:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Parse hotel_id from selection
hotel_id = None if property_choice == "All Properties" else property_choice.split(" (")[0]

# Fetch KPI Summary
try:
    current, prior = fetch_executive_kpi_summary(start_date, end_date, hotel_id)
except Exception as e:
    st.error(f"Could not load KPIs: {e}")
    current, prior = None, None

# Executive KPI Row (5 KPIs)
if current is None:
    st.info("No reservation data in the selected range.")
else:
    def get_val(d, key):
        return d.get(key) if d else None

    def fmt_revenue(v):
        if v is None: return "—"
        if v >= 1e9: return f"${v/1e9:.1f}B"
        if v >= 1e6: return f"${v/1e6:.1f}M"
        return f"${v:,.0f}"

    def fmt_adr(v):
        if v is None: return "—"
        return f"${v:,.0f}"

    def fmt_pct(v):
        if v is None: return "—"
        return f"{v*100:.1f}%"

    def fmt_revpar(v):
        if v is None: return "—"
        return f"${v:,.0f}"

    def calc_delta_pct(cur, prv):
        """Return % change vs prior, defaulting to 0 if either value is missing."""
        if cur is None or prv is None or prv == 0:
            return 0.0
        return (cur - prv) / abs(prv) * 100

    # Fetch sparkline data once (reused for all 4 KPIs that have sparklines)
    spark_data = fetch_sparkline_data(start_date, end_date, hotel_id)

    def _spark(col_name):
        """Return a two-column DataFrame (date, value) suitable for executive_kpi_card."""
        if spark_data.empty or col_name not in spark_data.columns:
            return None
        return spark_data.rename(columns={'business_date': 'date', col_name: 'value'})[['date', 'value']]

    # Determine status for each KPI
    rev_status = determine_status("revenue", get_val(current, "total_revenue"), get_val(prior, "total_revenue"))
    adr_status = determine_status("adr", get_val(current, "adr"), get_val(prior, "adr"))
    occ_status = determine_status("occupancy", get_val(current, "occupancy"), get_val(prior, "occupancy"))
    revpar_status = determine_status("revpar", get_val(current, "revpar"), get_val(prior, "revpar"))
    canc_status = determine_status("cancellation", get_val(current, "cancellation_rate"), get_val(prior, "cancellation_rate"))

    # KPI Cards Row — use executive_kpi_card which includes inline sparkline via _build_sparkline_svg
    kpi_cols = st.columns(5)

    with kpi_cols[0]:
        executive_kpi_card(
            label="Revenue",
            value=fmt_revenue(get_val(current, "total_revenue")),
            delta_pct=calc_delta_pct(get_val(current, "total_revenue"), get_val(prior, "total_revenue")),
            sparkline_data=_spark("total_revenue"),
            status=rev_status,
        )

    with kpi_cols[1]:
        executive_kpi_card(
            label="ADR",
            value=fmt_adr(get_val(current, "adr")),
            delta_pct=calc_delta_pct(get_val(current, "adr"), get_val(prior, "adr")),
            sparkline_data=_spark("adr"),
            status=adr_status,
        )

    with kpi_cols[2]:
        executive_kpi_card(
            label="Occupancy",
            value=fmt_pct(get_val(current, "occupancy")),
            delta_pct=calc_delta_pct(get_val(current, "occupancy"), get_val(prior, "occupancy")),
            sparkline_data=_spark("occupancy"),
            status=occ_status,
        )

    with kpi_cols[3]:
        executive_kpi_card(
            label="RevPAR",
            value=fmt_revpar(get_val(current, "revpar")),
            delta_pct=calc_delta_pct(get_val(current, "revpar"), get_val(prior, "revpar")),
            sparkline_data=_spark("revpar"),
            status=revpar_status,
        )

    with kpi_cols[4]:
        executive_kpi_card(
            label="Cancellation Rate",
            value=fmt_pct(get_val(current, "cancellation_rate")),
            delta_pct=calc_delta_pct(get_val(current, "cancellation_rate"), get_val(prior, "cancellation_rate")),
            sparkline_data=None,  # no sparkline for cancellation (not in SPARKLINE_SQL)
            status=canc_status,
        )

# Tab Bar
tab = executive_tab_bar(st.session_state['exec_active_tab'])
active_tab = st.session_state['exec_active_tab']

# Tab Content
if active_tab == 'overview':
    # Overview: Portfolio trend + 12-month trend
    col1, col2 = st.columns([2, 1])

    with col1:
        section_title("Portfolio Trend (12 Months)")
        trend_df = fetch_executive_kpi_daily(
            date.today() - timedelta(days=365), date.today(), hotel_id
        )
        if not trend_df.empty:
            import altair as alt
            base = alt.Chart(trend_df).encode(x=alt.X('business_date:T', title='Date'))
            revenue_line = base.mark_line(color='var(--accent-blue)', strokeWidth=2).encode(
                y=alt.Y('total_revenue:Q', title='Revenue', axis=alt.Axis(format='$,.0f')),
                tooltip=[alt.Tooltip('business_date:T'), alt.Tooltip('total_revenue:Q', format='$,.0f')]
            )
            occ_line = base.mark_line(color='var(--kpi-positive)', strokeWidth=2, strokeDash=[4, 4]).encode(
                y=alt.Y('occupancy:Q', title='Occupancy', axis=alt.Axis(format='%')),
                tooltip=[alt.Tooltip('business_date:T'), alt.Tooltip('occupancy:Q', format='.1%')]
            )
            chart_container(alt.layer(revenue_line, occ_line).resolve_scale(y='independent').properties(height=350), height=380)

    with col2:
        section_title("Key Metrics Summary")
        st.markdown(f"""
        <div class="exec-summary-card">
            <div class="exec-summary-row">
                <span>Properties Active</span>
                <strong>{len(fetch_executive_properties())}</strong>
            </div>
            <div class="exec-summary-row">
                <span>Date Range</span>
                <strong>{start_date} – {end_date}</strong>
            </div>
            <div class="exec-summary-row">
                <span>Total Room Nights</span>
                <strong>{fetch_executive_kpi_daily(start_date, end_date, hotel_id)['room_nights'].sum():,.0f}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Monthly Revenue bar chart
    monthly_df = fetch_monthly_revenue(start_date, end_date, hotel_id)
    if not monthly_df.empty:
        monthly_df['month_label'] = pd.to_datetime(monthly_df['month']).dt.strftime('%b %Y')
        section_title("Revenue by Month")
        import altair as alt
        bar = alt.Chart(monthly_df).mark_bar(color='var(--accent-blue)').encode(
            x=alt.X('month_label:N', sort=list(monthly_df['month_label']), title='Month'),
            y=alt.Y('monthly_revenue:Q', title='Revenue', axis=alt.Axis(format='$,.0f')),
            tooltip=[
                alt.Tooltip('month_label:N', title='Month'),
                alt.Tooltip('monthly_revenue:Q', title='Revenue', format='$,.0f'),
                alt.Tooltip('monthly_room_nights:Q', title='Room Nights', format=','),
            ]
        )
        text = bar.mark_text(align='center', baseline='bottom', dy=-4, fontSize=11).encode(
            text=alt.Text('monthly_revenue:Q', format='$,.0f')
        )
        chart_container(
            alt.layer(bar, text).properties(height=300),
            height=330
        )

elif active_tab == 'properties':
    section_title("Property Portfolio Comparison")
    portfolio_df = fetch_property_portfolio(start_date, end_date, hotel_id)
    if not portfolio_df.empty:
        # Add status column
        portfolio_df['status'] = portfolio_df.apply(
            lambda r: 'critical' if r.get('risk_flag', 0) > 0
            else 'at_risk' if r.get('occupancy', 1) < 0.6
            else 'on_track', axis=1
        )
        property_portfolio_table(portfolio_df)

elif active_tab == 'budget':
    section_title("Budget vs Actual")
    st.info("Budget data not yet available. Requires budget/target tables in warehouse.")

elif active_tab == 'forecast':
    section_title("Forecast")
    st.info("Forecast models not yet implemented. Requires ML pipeline integration.")

st.caption("ErasOpera Executive Dashboard — Real-time hospitality portfolio intelligence")