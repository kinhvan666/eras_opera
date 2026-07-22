import pandas as pd
import altair as alt
import streamlit as st

from data.repository import fetch_revenue_actual, fetch_revenue_breakdown
from ui.components import chart_wrapper
from ui.i18n import t, t_code

from ui.theme import chart_colors

# Vega-Lite expression: abbreviate VND values on axes
VND_LABEL_EXPR = (
    "datum.value >= 1e9 ? format(datum.value / 1e9, '.1f') + 'B' : "
    "datum.value >= 1e6 ? format(datum.value / 1e6, '.0f') + 'M' : "
    "datum.value >= 1e3 ? format(datum.value / 1e3, '.0f') + 'K' : "
    "format(datum.value, ',.0f')"
)

CATEGORY_ORDER  = ["Room", "FnB", "ServiceCharge", "Other"]


def _fmt_label(v):
    if v >= 1e9: return f"₫{v/1e9:.1f}B"
    if v >= 1e6: return f"₫{v/1e6:.0f}M"
    if v >= 1e3: return f"₫{v/1e3:.0f}K"
    return f"₫{v:,.0f}"


def _gradient_hbar(data, x_col, y_col, x_title, y_title, top_n=8):
    C = chart_colors()
    """Horizontal bar chart with gradient color ranking and concise code labels."""
    data = data.copy().sort_values(x_col, ascending=False)
    if len(data) > top_n:
        top_df = data.iloc[:top_n].copy()
        other_val = data.iloc[top_n:][x_col].sum()
        if other_val > 0:
            other_row = pd.DataFrame([{y_col: "OTH", x_col: other_val}])
            data = pd.concat([top_df, other_row], ignore_index=True)
        else:
            data = top_df

    data = data.sort_values(x_col, ascending=True)
    data["_label"] = data[x_col].apply(_fmt_label)
    data["_desc"] = data[y_col].apply(lambda x: t_code(y_col, x) if x != "OTH" else "Khác / Other")

    bars = alt.Chart(data).mark_bar(
        cornerRadiusTopRight=6, cornerRadiusBottomRight=6
    ).encode(
        y=alt.Y(f"{y_col}:N", sort="-x", title=y_title),
        x=alt.X(f"{x_col}:Q", title=x_title, axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
        color=alt.value(C["primary"]),
        tooltip=[
            alt.Tooltip(f"{y_col}:N", title="Mã / Code"),
            alt.Tooltip("_desc:N", title=y_title),
            alt.Tooltip(f"{x_col}:Q", format=",.0f", title=x_title),
        ],
    )
    labels = bars.mark_text(align="left", dx=6, fontSize=11, fontWeight=600, color=C["text_label"]).encode(
        text=alt.Text("_label:N")
    )
    return (bars + labels).properties(height=280)


def _gradient_vbar(data, x_col, y_col, x_title, y_title, top_n=7):
    C = chart_colors()
    """Vertical column chart with solid color for high contrast."""
    data = data.copy().sort_values(x_col, ascending=False)
    if len(data) > top_n:
        top_df = data.iloc[:top_n].copy()
        other_val = data.iloc[top_n:][x_col].sum()
        if other_val > 0:
            other_row = pd.DataFrame([{y_col: "OTH", x_col: other_val}])
            data = pd.concat([top_df, other_row], ignore_index=True)
        else:
            data = top_df

    data["_label"] = data[x_col].apply(_fmt_label)
    data["_desc"] = data[y_col].apply(lambda x: t_code(y_col, x) if x != "OTH" else "Khác / Other")

    bars = alt.Chart(data).mark_bar(
        cornerRadiusTopLeft=6, cornerRadiusTopRight=6
    ).encode(
        x=alt.X(f"{y_col}:N", sort="-y", title=y_title, axis=alt.Axis(labelAngle=-25)),
        y=alt.Y(f"{x_col}:Q", title=x_title, axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
        color=alt.value(C["primary"]),
        tooltip=[
            alt.Tooltip(f"{y_col}:N", title="Mã/Code"),
            alt.Tooltip("_desc:N", title=y_title),
            alt.Tooltip(f"{x_col}:Q", format=",.0f", title=x_title),
        ],
    )
    labels = bars.mark_text(align="center", baseline="bottom", dy=-8, fontSize=11, fontWeight=600, color=C["text_label"]).encode(
        text=alt.Text("_label:N")
    )
    return (bars + labels).properties(height=280)


def _donut_chart(data, x_col, y_col, x_title):
    C = chart_colors()
    """Donut chart for total revenue share."""
    total = data[x_col].sum()
    data = data.copy()
    data["_pct"] = data[x_col] / total if total > 0 else 0
    data["_pct_label"] = data["_pct"].apply(lambda p: f"{p*100:.1f}%")
    data["_val_label"] = data[x_col].apply(_fmt_label)
    
    # Map categories to friendly bilingual names
    lang = st.session_state.get("lang", "en")
    cat_translation = {
        "Room": "Room" if lang == "en" else "Doanh thu phòng",
        "FnB": "FnB" if lang == "en" else "FnB (Ẩm thực)",
        "ServiceCharge": "Service Charge" if lang == "en" else "Phí dịch vụ",
        "Other": "Other" if lang == "en" else "Khác"
    }
    data["_desc"] = data[y_col].apply(lambda x: cat_translation.get(x, x))

    base = alt.Chart(data).encode(
        theta=alt.Theta(f"{x_col}:Q", stack=True),
        color=alt.Color(
            f"{y_col}:N",
            scale=alt.Scale(domain=CATEGORY_ORDER, range=[C["primary"], C["positive"], C["warn"], C["gray"]]),
            legend=alt.Legend(title=t("axis.category") if lang == "vi" else "Category", orient="bottom")
        ),
        tooltip=[
            alt.Tooltip("_desc:N", title=t("axis.category")),
            alt.Tooltip(f"{x_col}:Q", format=",.0f", title=x_title),
            alt.Tooltip("_pct:Q", format=".1%", title="Tỷ lệ / Ratio")
        ]
    )
    
    donut = base.mark_arc(innerRadius=42, outerRadius=70)
    text = base.mark_text(radius=88, size=11, color=C["text_label"]).encode(
        text=alt.Text("_pct_label:N")
    )
    return (donut + text).properties(height=280)


def draw(start_date, end_date, hotel_id=None):
    C = chart_colors()
    cat_colors = [C["primary"], C["positive"], C["warn"], C["gray"]]
    df_actual = fetch_revenue_actual(start_date, end_date, hotel_id)
    bdf = fetch_revenue_breakdown(start_date, end_date, hotel_id)

    if "rev_tab_view" not in st.session_state:
        st.session_state["rev_tab_view"] = t("rev.by_month")
    by_month = st.radio(
        t("rev.view"), [t("rev.by_month"), t("rev.by_day")],
        horizontal=True, label_visibility="collapsed", key="rev_tab_view"
    ) == t("rev.by_month")

    # ── Row 1: Revenue trend & Overall composition ───────────────────────────
    if df_actual is not None and not df_actual.empty:
        df_chart = df_actual[df_actual["revenue_category"] != "Tax"].copy()
        if by_month:
            df_chart["month"] = (
                pd.to_datetime(df_chart["revenue_date"]).dt.to_period("M").astype(str)
            )
            src = df_chart.groupby(
                ["month", "revenue_category"], as_index=False
            )["posted_amount"].sum()
            x_enc     = alt.X("month:N", title=t("axis.month"),
                                sort=sorted(src["month"].unique()))
            x_tooltip = alt.Tooltip("month:N", title=t("axis.month"))
        else:
            src       = df_chart
            x_enc     = alt.X("revenue_date:T", title=t("axis.date"))
            x_tooltip = alt.Tooltip("revenue_date:T", title=t("axis.date"),
                                     format="%d/%m/%Y")
        title = t("chart.revenue_by_month") if by_month else t("chart.revenue_by_day")
        
        # Build the left trend chart
        x_col = "month" if by_month else "revenue_date"
        totals = src.groupby(x_col, as_index=False)["posted_amount"].sum()
        totals["_label"] = totals["posted_amount"].apply(_fmt_label)
        x_enc_tot = alt.X(f"{x_col}:N", title=t("axis.month") if by_month else t("axis.date"),
                            sort=sorted(src[x_col].unique()) if by_month else None)
        y_max = totals["posted_amount"].max() * 1.15

        if by_month:
            bars = alt.Chart(src).mark_bar(
                cornerRadiusTopLeft=2, cornerRadiusTopRight=2
            ).encode(
                x=x_enc,
                y=alt.Y("sum(posted_amount):Q", title=t("axis.revenue"),
                        axis=alt.Axis(labelExpr=VND_LABEL_EXPR),
                        scale=alt.Scale(domainMax=y_max)),
                color=alt.Color(
                    "revenue_category:N", title=t("axis.category"),
                    scale=alt.Scale(domain=CATEGORY_ORDER, range=cat_colors),
                    legend=None
                ),
                order=alt.Order("revenue_category:N", sort="ascending"),
                tooltip=[
                    x_tooltip,
                    alt.Tooltip("revenue_category:N", title=t("axis.category")),
                    alt.Tooltip("sum(posted_amount):Q", format=",.0f",
                                title=t("axis.revenue")),
                ],
            ).properties(height=300)

            labels = alt.Chart(totals).mark_text(
                align="center", baseline="bottom", dy=-4, fontSize=13, color=C["text_label"]
            ).encode(
                x=x_enc_tot,
                y=alt.Y("posted_amount:Q"),
                text=alt.Text("_label:N"),
            )
            chart = bars + labels
        else:
            # Daily view uses smooth stacked Area chart instead of cluttered thin bars
            chart = alt.Chart(src).mark_area(
                opacity=0.7,
                interpolate="monotone"
            ).encode(
                x=x_enc,
                y=alt.Y("sum(posted_amount):Q", title=t("axis.revenue"),
                        axis=alt.Axis(labelExpr=VND_LABEL_EXPR)),
                color=alt.Color(
                    "revenue_category:N", title=t("axis.category"),
                    scale=alt.Scale(domain=CATEGORY_ORDER, range=cat_colors),
                    legend=None
                ),
                order=alt.Order("revenue_category:N", sort="ascending"),
                tooltip=[
                    x_tooltip,
                    alt.Tooltip("revenue_category:N", title=t("axis.category")),
                    alt.Tooltip("sum(posted_amount):Q", format=",.0f",
                                title=t("axis.revenue")),
                ],
            ).properties(height=300)

        # Columns layout: 70% Trend Chart, 30% Overall Donut Chart
        col_left, col_right = st.columns([7, 3])
        with col_left:
            with chart_wrapper(title, height=380):
                st.altair_chart(chart, use_container_width=True)
        with col_right:
            with chart_wrapper(t("chart.revenue_by_segment_section"), height=380):
                donut_df = src.groupby("revenue_category", as_index=False)["posted_amount"].sum()
                st.altair_chart(_donut_chart(donut_df, "posted_amount", "revenue_category", t("axis.revenue")), use_container_width=True)
    else:
        st.info(t("msg.no_posting"))

    # ── Row 2: Market Segment + Room Type ────────────────────────────────────
    if not bdf.empty:
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            seg = (bdf.groupby("market_code", as_index=False)["revenue"]
                      .sum().sort_values("revenue", ascending=False))
            with chart_wrapper(t("chart.revenue_by_segment"), height=360):
                st.altair_chart(
                    _gradient_hbar(seg, "revenue", "market_code",
                                  t("axis.revenue"), t("axis.segment")),
                    use_container_width=True,
                )
        with col2:
            room = (bdf.groupby("room_type", as_index=False)["revenue"]
                       .sum().sort_values("revenue", ascending=False))
            with chart_wrapper(t("chart.revenue_by_roomtype"), height=360):
                st.altair_chart(
                    _gradient_vbar(room, "revenue", "room_type",
                                  t("axis.revenue"), t("axis.room_type")),
                    use_container_width=True,
                )
    else:
        st.info(t("msg.no_breakdown"))
