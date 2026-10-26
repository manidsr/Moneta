"""Local web server for the Moneta dashboard (read-only for now).

    python -m moneta_sync.server --db moneta.db --html ../Moneta.html --port 8787

Then open http://127.0.0.1:8787  -- it listens on 127.0.0.1 only, so your
financial data never leaves this computer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .db import connect


def transactions(db: str) -> list[dict]:
    conn = connect(db)
    try:
        rows = conn.execute(
            "SELECT id, date, type, amount, description, cat, note, ref, bal, src, st, created "
            "FROM transactions ORDER BY date, id").fetchall()
    finally:
        conn.close()
    out = []
    for id_, date, typ, amt, desc, cat, note, ref, bal, src, st, created in rows:
        out.append({"id": id_, "date": date, "type": typ, "amount": amt, "desc": desc,
                    # not categorised yet -> special "Uncategorized" ids the dashboard knows
                    "cat": cat or ("unx" if typ == "expense" else "uni"),
                    "note": note or "", "ref": ref or "", "bal": bal, "src": src,
                    "st": st, "created": created})
    return out


def sync_info(db: str) -> dict:
    conn = connect(db)
    try:
        ok = conn.execute("SELECT MAX(ran_at) FROM sync_runs WHERE error IS NULL").fetchone()[0]
        if ok is None:
            ok = conn.execute("SELECT MAX(created) FROM transactions").fetchone()[0]
        since = int(time.time() * 1000) - 86_400_000
        fail = conn.execute("SELECT COUNT(*) FROM sync_runs WHERE error IS NOT NULL AND ran_at > ?",
                            (since,)).fetchone()[0]
        last = conn.execute("SELECT invalid FROM sync_runs ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    return {"ok": ok or 0, "fail": fail, "pending": last[0] if last else 0}


def make_handler(db: str, html: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            host = self.headers.get("Host", "").rsplit(":", 1)[0]
            if host not in ("127.0.0.1", "localhost"):  # blocks DNS-rebinding tricks
                return self._send(403, b"forbidden", "text/plain")
            path = self.path.split("?")[0]
            try:
                if path in ("/", "/Moneta.html"):
                    return self._send(200, Path(html).read_bytes(), "text/html; charset=utf-8")
                if path == "/api/transactions":
                    return self._send(200, json.dumps(transactions(db)).encode(), "application/json")
                if path == "/api/sync":
                    return self._send(200, json.dumps(sync_info(db)).encode(), "application/json")
                self._send(404, b"not found", "text/plain")
            except Exception as e:  # noqa: BLE001
                self._send(500, f"{type(e).__name__}: {e}".encode(), "text/plain; charset=utf-8")

        def log_message(self, *a) -> None:
            pass

    return Handler


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="moneta_sync.server", description="Moneta dashboard server")
    p.add_argument("--db", default=os.environ.get("MONETA_DB", "moneta.db"))
    p.add_argument("--html", default=os.environ.get("MONETA_HTML"))
    p.add_argument("--port", type=int, default=8787)
    a = p.parse_args(argv)
    html = a.html
    if not html:
        for c in ("Moneta.html", "../Moneta.html"):
            if Path(c).exists():
                html = c
                break
    if not html or not Path(html).exists():
        p.error("Moneta.html not found; pass --html PATH")
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(a.db, html))
    print(f"Moneta dashboard: http://127.0.0.1:{a.port}   (db={a.db}, Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
