# dashboard_v2/pages/admin.py
# Admin panel: User Management (CRUD + property assignment).
# Accessible only to admin users.
# Called from app.py via ?page=admin (auth guards already applied).

import streamlit as st
from pathlib import Path

from auth.session import get_current_user
from auth.db import (
    list_users,
    create_user,
    update_user,
    delete_user,
    reset_password,
    username_exists,
    get_user_by_id,
)
from data.repository import fetch_properties
from ui.i18n import t


def render_admin():
    st.markdown(f'<a href="?" target="_self" style="font-size:13px;color:var(--text-secondary);text-decoration:none">&larr; {t("admin.back_to_dashboard")}</a>', unsafe_allow_html=True)
    st.title(f"⚙ {t('admin.title')}")

    # ── Load properties for picker ───────────────────────────────────────────────
    try:
        props_df = fetch_properties()
        all_hotel_ids = props_df["hotel_id"].tolist()
        hotel_labels  = {
            row["hotel_id"]: (row["hotel_name"] or row["hotel_id"])
            for _, row in props_df.iterrows()
        }
    except Exception:
        all_hotel_ids = []
        hotel_labels  = {}

    current_admin = get_current_user()


    def _property_picker(key: str, default: list | None = None) -> list | None:
        all_label = t("admin.all_properties")
        options   = [all_label] + all_hotel_ids
        defaults  = [all_label] if default is None else default

        selected = st.multiselect(
            t("admin.properties"),
            options=options,
            default=defaults,
            format_func=lambda x: hotel_labels.get(x, x) if x != all_label else all_label,
            key=key,
        )
        if all_label in selected or not selected:
            return None
        return selected


    def _fmt_hotels(allowed: list | None) -> str:
        if allowed is None:
            return "✦ All"
        return ", ".join(hotel_labels.get(h, h) for h in allowed)


    tab_list, tab_create, tab_edit = st.tabs([
        t("admin.tab_list"),
        t("admin.tab_create"),
        t("admin.tab_edit"),
    ])

    # ── Tab 1: User List ────────────────────────────────────────────────────────
    with tab_list:
        users = list_users()
        if not users:
            st.info("No users yet.")
        else:
            for u in users:
                with st.expander(
                    f"{'👑 ' if u['is_admin'] else '👤 '}{u['username']}"
                    f"{'  🔴 inactive' if not u['is_active'] else ''}",
                    expanded=False,
                ):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**{t('admin.display_name')}:** {u['display_name'] or '—'}")
                    c1.markdown(f"**{t('admin.email')}:** {u['email'] or '—'}")
                    c2.markdown(f"**{t('admin.is_admin')}:** {'✓' if u['is_admin'] else '✗'}")
                    c2.markdown(f"**{t('admin.is_active')}:** {'✓' if u['is_active'] else '✗'}")
                    c3.markdown(f"**{t('admin.properties')}:** {_fmt_hotels(u['allowed_hotel_ids'])}")
                    last = u["last_login"]
                    c3.markdown(f"**{t('admin.last_login')}:** {last.strftime('%d/%m/%Y %H:%M') if last else t('admin.never')}")

                    col_a, _, col_c = st.columns([1, 1, 1])

                    if u["id"] != current_admin["id"]:
                        if u["is_active"]:
                            if col_a.button(t("admin.deactivate"), key=f"deact_{u['id']}"):
                                update_user(u["id"], is_active=False)
                                st.rerun()
                        else:
                            if col_a.button(t("admin.activate"), key=f"act_{u['id']}"):
                                update_user(u["id"], is_active=True)
                                st.rerun()

                    admin_count = sum(1 for x in users if x["is_admin"] and x["is_active"])
                    can_delete  = u["id"] != current_admin["id"] and not (u["is_admin"] and admin_count <= 1)
                    if can_delete:
                        if col_c.button(t("admin.delete"), key=f"del_{u['id']}", type="secondary"):
                            delete_user(u["id"])
                            st.success(t("admin.success_deleted"))
                            st.rerun()

    # ── Tab 2: Create User ──────────────────────────────────────────────────────
    with tab_create:
        with st.form("create_user_form"):
            username     = st.text_input(t("admin.username"))
            display_name = st.text_input(t("admin.display_name"))
            email        = st.text_input(t("admin.email"))
            password     = st.text_input(t("admin.password"), type="password")
            confirm_pw   = st.text_input(t("admin.confirm_password"), type="password")
            is_admin_cb  = st.checkbox(t("admin.is_admin"), value=False)
            submitted    = st.form_submit_button(t("admin.create"), type="primary")

        new_hotel_ids = _property_picker("create_hotels")

        if submitted:
            err = None
            if not username.strip():
                err = t("admin.err_username_empty")
            elif not password:
                err = t("admin.err_password_empty")
            elif password != confirm_pw:
                err = t("admin.err_password_mismatch")
            elif username_exists(username.strip().lower()):
                err = t("admin.err_username_taken")

            if err:
                st.error(err)
            else:
                create_user(
                    username=username.strip().lower(),
                    plain_password=password,
                    display_name=display_name.strip() or username.strip(),
                    email=email.strip(),
                    is_admin=is_admin_cb,
                    allowed_hotel_ids=new_hotel_ids,
                    created_by=current_admin["username"],
                )
                st.success(t("admin.success_created"))
                st.rerun()

    # ── Tab 3: Edit User ────────────────────────────────────────────────────────
    with tab_edit:
        users = list_users()
        if not users:
            st.info("No users yet.")
        else:
            user_options = {f"{u['username']} ({u['display_name'] or ''})": u["id"] for u in users}
            selected_label = st.selectbox(t("admin.select_user"), list(user_options.keys()))
            selected_id    = user_options[selected_label]
            u = get_user_by_id(selected_id)

            if u:
                st.divider()
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Profile")
                    with st.form("edit_profile_form"):
                        new_display = st.text_input(t("admin.display_name"), value=u["display_name"] or "")
                        new_email   = st.text_input(t("admin.email"), value=u["email"] or "")
                        new_is_admin = st.checkbox(
                            t("admin.is_admin"),
                            value=u["is_admin"],
                            disabled=(u["id"] == current_admin["id"]),
                        )
                        save_profile = st.form_submit_button(t("admin.save"), type="primary")

                    if save_profile:
                        update_user(
                            u["id"],
                            display_name=new_display.strip(),
                            email=new_email.strip(),
                            is_admin=new_is_admin,
                        )
                        st.success(t("admin.success_updated"))
                        st.rerun()

                with col2:
                    st.subheader(t("admin.properties"))
                    current_hotels = u["allowed_hotel_ids"]
                    edit_hotel_ids = _property_picker("edit_hotels", default=current_hotels)

                    if st.button(t("admin.save") + " properties", key="save_hotels"):
                        if edit_hotel_ids is None:
                            update_user(u["id"], _reset_hotel_ids_to_null=True)
                        else:
                            update_user(u["id"], allowed_hotel_ids=edit_hotel_ids)
                        st.success(t("admin.success_updated"))
                        st.rerun()

                st.divider()
                st.subheader(t("admin.reset_password"))
                with st.form("reset_pw_form"):
                    new_pw  = st.text_input(t("admin.new_password"), type="password")
                    conf_pw = st.text_input(t("admin.confirm_password"), type="password")
                    reset   = st.form_submit_button(t("admin.reset_password"))

                if reset:
                    if not new_pw:
                        st.error(t("admin.err_password_empty"))
                    elif new_pw != conf_pw:
                        st.error(t("admin.err_password_mismatch"))
                    else:
                        reset_password(u["id"], new_pw)
                        st.success(t("admin.success_password"))
