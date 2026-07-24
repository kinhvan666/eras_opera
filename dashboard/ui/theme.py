import streamlit as st

_DARK = {
    "primary": "#1D4ED8", "accent": "#3B82F6", "warn": "#F59E0B",
    "gray": "#ADB5BD", "text_label": "#E2E8F0", "band": "#334155",
    "positive": "#34D399", "negative": "#F87171",
}
_LIGHT = {
    "primary": "#1E40AF", "accent": "#2563EB", "warn": "#D97706",
    "gray": "#475569", "text_label": "#0F172A", "band": "#E2E8F0",
    "positive": "#047857", "negative": "#B91C1C",
}

def current_theme() -> str:
    if "ui_theme" in st.session_state and st.session_state["ui_theme"]:
        return st.session_state["ui_theme"]
    try:
        if hasattr(st, "context") and hasattr(st.context, "theme") and st.context.theme:
            t_type = getattr(st.context.theme, "type", None)
            if t_type:
                return t_type
    except Exception:
        pass
    return "light"

# Get the appropriate chart_colors for the current theme
def chart_colors() -> dict:
    return _LIGHT if current_theme() == "light" else _DARK
