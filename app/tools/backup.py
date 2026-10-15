"""Safe backup of the HRM WorkSpace database (works while the server is running).

    python -m tools.backup            → backups/hrm-YYYYMMDD-HHMM.db  (keeps the newest 30)
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from hrm import config

KEEP = 30


def main() -> int:
    src = config.DATA_DIR / "hrm.db"
    if not src.exists():
        print(f"No database yet: {src}")
        return 1
    out_dir = config.APP_DIR / "backups"
    out_dir.mkdir(exist_ok=True)
    dst = out_dir / f"hrm-{datetime.now():%Y%m%d-%H%M}.db"
    with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
        s.backup(d)                       # consistent copy even with WAL / open connections
    olds = sorted(out_dir.glob("hrm-*.db"))[:-KEEP]
    for f in olds:
        f.unlink()
    print(f"Backup saved: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
