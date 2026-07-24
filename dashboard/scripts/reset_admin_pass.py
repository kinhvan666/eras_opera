import sys
import argparse
import getpass
import os

# Add the parent directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth.db import get_user_by_username, reset_password, revoke_all_user_sessions, setup_auth_tables

def main():
    parser = argparse.ArgumentParser(description="Reset user password and revoke all active sessions.")
    parser.add_argument("--username", type=str, default="admin", help="Username to reset (default: admin)")
    args = parser.parse_args()

    username = args.username

    # Ensure tables exist
    setup_auth_tables()

    user = get_user_by_username(username)
    if not user:
        print(f"Error: User '{username}' not found.")
        sys.exit(1)

    print(f"Resetting password for user: {username}")
    new_password = getpass.getpass("New Password: ")
    confirm_password = getpass.getpass("Confirm New Password: ")

    if not new_password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    if new_password != confirm_password:
        print("Error: Passwords do not match.")
        sys.exit(1)

    reset_password(user["id"], new_password)
    revoke_all_user_sessions(user["id"])
    
    print(f"Successfully updated password for '{username}' and revoked all previous sessions.")

if __name__ == "__main__":
    main()
