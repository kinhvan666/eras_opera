# dashboard_v2/auth/db.py
# Database operations for auth.users table.
# All queries use parameterized inputs — no string interpolation.

import secrets
import psycopg2
import psycopg2.extras
from typing import Optional

from config.settings import DATABASE_URL
from auth.utils import hash_password


# ---------------------------------------------------------------------------
# Schema setup (called once at app startup)
# ---------------------------------------------------------------------------

SETUP_SQL = """
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id                SERIAL PRIMARY KEY,
    username          TEXT NOT NULL UNIQUE,
    email             TEXT,
    password_hash     TEXT NOT NULL,
    display_name      TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    is_admin          BOOLEAN NOT NULL DEFAULT false,
    -- NULL = all properties, non-null array = specific hotel_ids only
    allowed_hotel_ids TEXT[],
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login        TIMESTAMPTZ,
    created_by        TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_username ON auth.users(username);

CREATE TABLE IF NOT EXISTS auth.user_sessions (
    token       TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);
"""


def setup_auth_tables() -> None:
    """Create auth schema, users table, and user_sessions table if they don't exist yet."""
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(SETUP_SQL)
        conn.commit()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def _row_to_dict(row) -> dict:
    return dict(row)


def get_user_by_username(username: str) -> Optional[dict]:
    """Return user row as dict or None if not found."""
    sql = """
        SELECT id, username, email, password_hash, display_name,
               is_active, is_admin, allowed_hotel_ids, created_at, last_login
        FROM auth.users
        WHERE username = %s
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (username,))
            row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    sql = """
        SELECT id, username, email, password_hash, display_name,
               is_active, is_admin, allowed_hotel_ids, created_at, last_login
        FROM auth.users WHERE id = %s
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def list_users() -> list[dict]:
    """Return all users ordered by username (password_hash excluded)."""
    sql = """
        SELECT id, username, email, display_name, is_active, is_admin,
               allowed_hotel_ids, created_at, last_login, created_by
        FROM auth.users
        ORDER BY username
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def create_user(
    username: str,
    plain_password: str,
    display_name: str = "",
    email: str = "",
    is_admin: bool = False,
    allowed_hotel_ids: Optional[list[str]] = None,
    created_by: str = "system",
) -> dict:
    """Create a new user and return the created row."""
    sql = """
        INSERT INTO auth.users
            (username, email, password_hash, display_name,
             is_active, is_admin, allowed_hotel_ids, created_by)
        VALUES (%s, %s, %s, %s, true, %s, %s, %s)
        RETURNING id, username, email, display_name,
                  is_active, is_admin, allowed_hotel_ids, created_at
    """
    pw_hash = hash_password(plain_password)
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (
                username, email or None, pw_hash,
                display_name or username,
                is_admin,
                allowed_hotel_ids,  # None → NULL (all properties)
                created_by,
            ))
            row = cur.fetchone()
        conn.commit()
    return dict(row)


def update_user(
    user_id: int,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    allowed_hotel_ids: Optional[list] = None,
    _reset_hotel_ids_to_null: bool = False,
) -> None:
    """Partial update — only non-None fields are changed.
    Pass _reset_hotel_ids_to_null=True to explicitly set allowed_hotel_ids to NULL (all properties).
    """
    fields = []
    values = []

    if display_name is not None:
        fields.append("display_name = %s")
        values.append(display_name)
    if email is not None:
        fields.append("email = %s")
        values.append(email or None)
    if is_active is not None:
        fields.append("is_active = %s")
        values.append(is_active)
    if is_admin is not None:
        fields.append("is_admin = %s")
        values.append(is_admin)
    if _reset_hotel_ids_to_null:
        fields.append("allowed_hotel_ids = NULL")
    elif allowed_hotel_ids is not None:
        fields.append("allowed_hotel_ids = %s")
        values.append(allowed_hotel_ids)

    if not fields:
        return

    values.append(user_id)
    sql = f"UPDATE auth.users SET {', '.join(fields)} WHERE id = %s"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()


def reset_password(user_id: int, new_plain_password: str) -> None:
    sql = "UPDATE auth.users SET password_hash = %s WHERE id = %s"
    pw_hash = hash_password(new_plain_password)
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pw_hash, user_id))
        conn.commit()


def delete_user(user_id: int) -> None:
    sql = "DELETE FROM auth.users WHERE id = %s"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
        conn.commit()


def record_last_login(user_id: int) -> None:
    sql = "UPDATE auth.users SET last_login = NOW() WHERE id = %s"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
        conn.commit()


def username_exists(username: str) -> bool:
    sql = "SELECT 1 FROM auth.users WHERE username = %s"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (username,))
            return cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Session token management (for persistent login across F5 refresh)
# ---------------------------------------------------------------------------

def create_user_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    sql = """
        INSERT INTO auth.user_sessions (token, user_id)
        VALUES (%s, %s)
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (token, user_id))
        conn.commit()
    return token


def get_user_by_session_token(token: str) -> Optional[dict]:
    sql = """
        SELECT u.id, u.username, u.email, u.display_name,
               u.is_active, u.is_admin, u.allowed_hotel_ids
        FROM auth.user_sessions s
        JOIN auth.users u ON s.user_id = u.id
        WHERE s.token = %s AND s.expires_at > NOW() AND u.is_active = true
    """
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (token,))
            row = cur.fetchone()
    return dict(row) if row else None


def delete_user_session(token: str) -> None:
    sql = "DELETE FROM auth.user_sessions WHERE token = %s"
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (token,))
        conn.commit()
