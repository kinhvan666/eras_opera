#!/usr/bin/env python3
"""
seed_admin.py — Tạo admin user đầu tiên.

Chạy một lần trên server sau khi deploy:
    cd /path/to/dashboard
    python scripts/seed_admin.py

Hoặc qua Docker:
    docker compose -f docker-compose.prod.yml run --rm dashboard \
        python scripts/seed_admin.py

Nếu username đã tồn tại, script sẽ báo và thoát mà không thay đổi gì.
"""

import sys
import os
import getpass

# Thêm parent dir vào path để import config và auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.db import setup_auth_tables, create_user, username_exists


def main():
    print("=" * 50)
    print("Eras Opera — Admin User Seed")
    print("=" * 50)

    # Setup tables
    print("\nSetting up auth tables...")
    setup_auth_tables()
    print("✓ Auth tables ready.")

    # Default values with interactive override
    print("\nEnter admin credentials (press Enter to use defaults):")

    username = input("Username [admin]: ").strip() or "admin"

    if username_exists(username.lower()):
        print(f"\n⚠ User '{username}' already exists. Skipping seed.")
        print("Use the admin panel to manage users.")
        sys.exit(0)

    display_name = input(f"Display name [{username.title()}]: ").strip() or username.title()
    email = input("Email (optional): ").strip() or None

    while True:
        password = getpass.getpass("Password: ")
        if not password:
            print("Password cannot be empty. Try again.")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match. Try again.")
            continue
        break

    # Create admin user
    user = create_user(
        username=username.lower(),
        plain_password=password,
        display_name=display_name,
        email=email,
        is_admin=True,
        allowed_hotel_ids=None,  # NULL = all properties
        created_by="seed_script",
    )

    print(f"\n✓ Admin user created:")
    print(f"  Username:     {user['username']}")
    print(f"  Display name: {user['display_name']}")
    print(f"  Admin:        {user['is_admin']}")
    print(f"  Properties:   All (no restriction)")
    print("\nYou can now log in to the dashboard.")


if __name__ == "__main__":
    main()
