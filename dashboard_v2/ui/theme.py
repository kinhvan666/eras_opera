import streamlit as st

_DARK = {
    "primary": "#1D4ED8", "accent": "#3B82F6", "warn": "#F59E0B",
    "gray": "#ADB5BD", "text_label": "#E2E8F0", "band": "#334155",
    "positive": "#34D399", "negative": "#F87171",
}
_LIGHT = {
    "primary": "#2563EB", "accent": "#3B82F6", "warn": "#D97706",
    "gray": "#64748B", "text_label": "#1E293B", "band": "#F1F5F9",
    "positive": "#059669", "negative": "#DC2626",
}

def current_theme() -> str:
    return st.session_state.get("ui_theme", "dark")

# Get the appropriate chart_colors for the current theme
def chart_colors() -> dict:
    return _LIGHT if current_theme() == "light" else _DARK
