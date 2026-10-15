"""Reset a user's password from the main PC (when nobody can log in as admin).

    python -m tools.reset_password admin
"""
import getpass
import sys

from sqlalchemy import select

from hrm.auth import hash_password
from hrm.db import init_engine, session_scope
from hrm.models import User, audit


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "admin"
    init_engine()
    with session_scope() as db:
        u = db.scalar(select(User).where(User.username == name))
        if not u:
            print(f"User not found: {name}")
            return 1
        pw = getpass.getpass(f"New password for {name} (min 6 chars): ")
        if len(pw) < 6 or pw != getpass.getpass("Repeat: "):
            print("Not changed (too short or the two entries differ).")
            return 1
        u.password_hash, u.active = hash_password(pw), True
        audit(db, None, "reset_password_cli", "user", u.id, {})
    print("Password changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
