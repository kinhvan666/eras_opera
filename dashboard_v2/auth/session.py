# dashboard_v2/auth/session.py
# Session management and login/logout logic.
# Login page UI is rendered here to keep app.py clean.

from pathlib import Path
import streamlit as st

from auth.db import (
    get_user_by_username,
    record_last_login,
    setup_auth_tables,
)
from auth.utils import verify_password
from ui.i18n import t

# Session key for the authenticated user dict
_USER_KEY = "auth_user"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_user() -> dict | None:
    """Return the currently logged-in user dict or None."""
    return st.session_state.get(_USER_KEY)


def is_logged_in() -> bool:
    return _USER_KEY in st.session_state and st.session_state[_USER_KEY] is not None


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and user.get("is_admin"))


def logout() -> None:
    st.session_state.pop(_USER_KEY, None)
    st.rerun()


def require_login() -> dict:
    """Ensure user is logged in. If not, render login page and stop execution.
    Returns the current user dict when already authenticated.
    """
    if "_auth_tables_setup" not in st.session_state:
        try:
            setup_auth_tables()
            st.session_state["_auth_tables_setup"] = True
        except Exception as e:
            st.error(f"Database setup error: {e}")
            st.stop()

    if not is_logged_in():
        _render_login_page()
        st.stop()

    return get_current_user()


def require_admin() -> None:
    """Stop execution with error if current user is not admin."""
    if not is_admin():
        st.error("⛔ Bạn không có quyền truy cập trang này.")
        st.stop()


# ---------------------------------------------------------------------------
# Internal: login attempt
# ---------------------------------------------------------------------------

def _attempt_login(username: str, password: str) -> str | None:
    """Try to log in. Returns error message string or None on success."""
    if not username or not password:
        return t("auth.error_empty")

    user = get_user_by_username(username.strip().lower())

    # Deliberate: same error for "not found" and "wrong password" — no user enumeration
    if user is None or not user["is_active"]:
        return t("auth.error_invalid")

    if not verify_password(password, user["password_hash"]):
        return t("auth.error_invalid")

    # Success — store safe subset in session (no password_hash)
    st.session_state[_USER_KEY] = {
        "id":                user["id"],
        "username":          user["username"],
        "display_name":      user["display_name"] or user["username"],
        "email":             user["email"],
        "is_admin":          user["is_admin"],
        "allowed_hotel_ids": user["allowed_hotel_ids"],
    }
    record_last_login(user["id"])
    return None


# ---------------------------------------------------------------------------
# Internal: login page rendering
# ---------------------------------------------------------------------------

def _render_login_page() -> None:
    logo_path = Path(__file__).parent.parent / "logo.png"
    theme_css = Path(__file__).parent.parent / "styles" / "theme.css"

    if theme_css.exists():
        st.markdown(f"<style>{theme_css.read_text()}</style>", unsafe_allow_html=True)

    import base64
    logo_b64 = ""
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

    # Center form using columns
    st.markdown('<div style="margin-top:40px"></div>', unsafe_allow_html=True)
    _, col_form, _ = st.columns([3, 2, 3])
    with col_form:
        if logo_b64:
            st.markdown(f"""
            <div style="text-align:center;margin-bottom:24px">
                <img src="data:image/png;base64,{logo_b64}" style="height:56px;width:auto">
                <div style="font-size:24px;font-weight:700;background:linear-gradient(90deg,#FFFFFF 0%,#93C5FD 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.3px;margin-top:12px">{t('app.title')}</div>
                <div style="color:var(--text-secondary);font-size:14px;margin-top:-4px">{t('auth.subtitle')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align:center;margin-bottom:24px">
                <div style="font-size:24px;font-weight:700;background:linear-gradient(90deg,#FFFFFF 0%,#93C5FD 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.3px">{t('app.title')}</div>
            </div>
            """, unsafe_allow_html=True)

        if "login_error" not in st.session_state:
            st.session_state["login_error"] = ""

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                t("auth.username_label"),
                placeholder=t("auth.username_placeholder"),
                autocomplete="username",
            )
            password = st.text_input(
                t("auth.password_label"),
                type="password",
                placeholder=t("auth.password_placeholder"),
                autocomplete="current-password",
            )
            submitted = st.form_submit_button(
                t("auth.login_btn"),
                use_container_width=True,
                type="primary",
            )

            if submitted:
                err = _attempt_login(username, password)
                if err:
                    st.session_state["login_error"] = err
                else:
                    st.session_state["login_error"] = ""
                    st.rerun()

        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"], icon="🔒")

        st.markdown(f"""
        <div style="text-align:center;margin-top:24px;color:var(--text-secondary);font-size:12px">
            {t('auth.contact_admin')}
        </div>
        """, unsafe_allow_html=True)
