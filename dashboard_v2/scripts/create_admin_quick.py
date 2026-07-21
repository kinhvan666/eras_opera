"""Quick admin creation for testing — run inside container.
Usage: python scripts/create_admin_quick.py [password]
Default password from ADMIN_PASSWORD env var or auto-generated if neither provided.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.db import setup_auth_tables, create_user, username_exists

setup_auth_tables()
print("Auth tables ready.")

if not username_exists("admin"):
    pw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ADMIN_PASSWORD", "")
    if not pw:
        import secrets, string
        pw = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        auto = True
    else:
        auto = False

    u = create_user(
        username="admin",
        plain_password=pw,
        display_name="Administrator",
        is_admin=True,
        allowed_hotel_ids=None,
    )
    print(f"Created admin: {u['username']}")
    if auto:
        print(f"Auto-generated password: {pw}  (SAVE THIS — shown only once)")
    else:
        print("Password from ADMIN_PASSWORD env var or command-line argument.")
else:
    print("admin already exists — skipping.")
