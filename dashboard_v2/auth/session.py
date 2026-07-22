# dashboard_v2/auth/session.py
# Session management and login/logout logic.
# Login page UI is rendered here to keep app.py clean.

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from auth.db import (
    get_user_by_username,
    record_last_login,
    setup_auth_tables,
    create_user_session,
    get_user_by_session_token,
    delete_user_session,
)
from auth.utils import verify_password
from ui.i18n import t

# Session key for the authenticated user dict
_USER_KEY = "auth_user"
COOKIE_NAME = "erasopera_session"

# ---------------------------------------------------------------------------
# Cookie Helpers (Native HTTP + JS First-Party Cookie)
# ---------------------------------------------------------------------------

def _set_cookie(token: str, max_age_seconds: int = 14400) -> None:
    """Write first-party cookie directly to browser document.cookie."""
    js = f"""
    <script>
        try {{
            window.parent.document.cookie = "{COOKIE_NAME}={token}; path=/; max-age={max_age_seconds}; SameSite=Lax";
        }} catch(e) {{
            document.cookie = "{COOKIE_NAME}={token}; path=/; max-age={max_age_seconds}; SameSite=Lax";
        }}
    </script>
    """
    components.html(js, height=0, width=0)


def _delete_cookie() -> None:
    """Clear first-party cookie from browser."""
    js = f"""
    <script>
        try {{
            window.parent.document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        }} catch(e) {{
            document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        }}
    </script>
    """
    components.html(js, height=0, width=0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_user() -> dict | None:
    """Return the currently logged-in user dict or None."""
    return st.session_state.get(_USER_KEY)


def is_logged_in() -> bool:
    if _USER_KEY in st.session_state and st.session_state[_USER_KEY] is not None:
        return True

    # 1. Check Native Streamlit 1.54 HTTP Cookie header (100% synchronous on F5 refresh!)
    token = None
    try:
        token = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        token = None

    # 2. Check URL query parameters if link was opened directly
    if not token:
        token = st.query_params.get("session_token")
        if token:
            st.query_params.pop("session_token", None)

    if token:
        user = get_user_by_session_token(token)
        if user:
            st.session_state[_USER_KEY] = {
                "id":                user["id"],
                "username":          user["username"],
                "display_name":      user["display_name"] or user["username"],
                "email":             user["email"],
                "is_admin":          user["is_admin"],
                "allowed_hotel_ids": user["allowed_hotel_ids"],
            }
            # Ensure cookie is kept alive for 4h
            _set_cookie(token, max_age_seconds=14400)
            return True
        else:
            # Token invalid or expired in DB
            _delete_cookie()

    return False


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and user.get("is_admin"))


def logout() -> None:
    token = None
    try:
        token = st.context.cookies.get(COOKIE_NAME)
    except Exception:
        pass
    token = token or st.query_params.get("session_token")

    if token:
        delete_user_session(token)

    _delete_cookie()
    st.query_params.clear()
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

    # Success — store safe subset in session & persistent token
    st.session_state[_USER_KEY] = {
        "id":                user["id"],
        "username":          user["username"],
        "display_name":      user["display_name"] or user["username"],
        "email":             user["email"],
        "is_admin":          user["is_admin"],
        "allowed_hotel_ids": user["allowed_hotel_ids"],
    }
    token = create_user_session(user["id"])
    _set_cookie(token, max_age_seconds=14400)
    st.query_params.clear()
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
                <div style="font-size:24px;font-weight:700;background:linear-gradient(90deg,var(--title-gradient-from) 0%,var(--title-gradient-to) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.3px;margin-top:12px">{t('app.title')}</div>
                <div style="color:var(--text-secondary);font-size:14px;margin-top:-4px">{t('auth.subtitle')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align:center;margin-bottom:24px">
                <div style="font-size:24px;font-weight:700;background:linear-gradient(90deg,var(--title-gradient-from) 0%,var(--title-gradient-to) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.3px">{t('app.title')}</div>
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
