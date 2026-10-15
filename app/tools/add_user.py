"""Create (or update) a login on the main PC without opening the web UI.

    python -m tools.add_user            # asks for username, display name, role, password

Nothing is stored in code or Git — the account lives only in this PC's database (app/data/hrm.db).
Running it again for an existing username updates the display name / role / password.
"""
import getpass
import sys

from sqlalchemy import select

from hrm.auth import hash_password
from hrm.db import init_engine, session_scope
from hrm.models import ROLES, User, audit


def ask(prompt, default=""):
    v = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return v or default


def main() -> int:
    init_engine()
    username = ask("Username (ชื่อผู้ใช้สำหรับเข้าระบบ)")
    if len(username) < 2:
        print("Username must be at least 2 characters.")
        return 1
    with session_scope() as db:
        u = db.scalar(select(User).where(User.username == username))
        display = ask("Display name (ชื่อที่แสดง)", u.display_name if u else username)
        role = ask(f"Role {'/'.join(ROLES)}", u.role if u else "admin")
        if role not in ROLES:
            print(f"Role must be one of: {', '.join(ROLES)}")
            return 1
        pw = getpass.getpass("Password (min 6 chars, not shown while typing): ")
        if len(pw) < 6 or pw != getpass.getpass("Repeat password: "):
            print("Not saved (too short or the two entries differ).")
            return 1
        if u:
            u.display_name, u.role, u.password_hash, u.active = display, role, hash_password(pw), True
            audit(db, None, "update_user_cli", "user", u.id, {"role": role})
            print(f"Updated user '{username}' ({role}).")
        else:
            u = User(username=username, display_name=display, role=role, password_hash=hash_password(pw))
            db.add(u)
            db.flush()
            audit(db, None, "create_user_cli", "user", u.id, {"role": role})
            print(f"Created user '{username}' ({role}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
