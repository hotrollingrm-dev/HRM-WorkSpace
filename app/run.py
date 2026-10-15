"""Start HRM WorkSpace.

    python run.py              this computer only   → http://127.0.0.1:8000
    python run.py --lan        also tablets/phones on the same Wi-Fi/LAN
    python run.py --open       open the browser after start
"""
import argparse
import socket
import threading
import webbrowser

import uvicorn

from hrm import config
from hrm.main import create_app


def lan_ips() -> list[str]:
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))          # no packet is sent; picks the LAN interface
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="HRM WorkSpace server")
    ap.add_argument("--lan", action="store_true", help="listen on all interfaces so tablets on the same network can connect")
    ap.add_argument("--host", default=None, help="advanced: explicit bind address")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--open", action="store_true", help="open the browser after start")
    a = ap.parse_args()
    host = a.host or ("0.0.0.0" if a.lan else "127.0.0.1")

    app = create_app()
    line = "=" * 64
    print(f"\n{line}\n  HRM WorkSpace is running\n")
    print(f"  On this computer : http://127.0.0.1:{a.port}/")
    if host == "0.0.0.0":
        ips = lan_ips()
        for ip in ips:
            print(f"  Tablet / phone   : http://{ip}:{a.port}/m.html   (today's work)")
            print(f"  Tablet planner   : http://{ip}:{a.port}/")
        if not ips:
            print("  (no network address found — check Wi-Fi/LAN connection)")
    else:
        print("  Tablets cannot connect in this mode. Use start_for_tablets.bat (or --lan).")
    pw_file = config.DATA_DIR / "FIRST_ADMIN_PASSWORD.txt"
    if pw_file.exists():
        print(f"\n  First admin password saved in: {pw_file}")
        print("  Log in as 'admin', change the password, then delete that file.")
    print(f"\n  Data folder: {config.DATA_DIR}")
    print(f"  Keep this window open. Close it (or Ctrl+C) to stop.\n{line}\n")

    if a.open:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{a.port}/")).start()
    uvicorn.run(app, host=host, port=a.port, log_level="warning")
