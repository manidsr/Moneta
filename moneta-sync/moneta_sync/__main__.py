"""Usage:  python -m moneta_sync              (run once)
          python -m moneta_sync --interval 60 (run forever, every 60 s)
"""
import argparse
import logging
import os
import sys
import time

from .db import connect
from .importer import import_once


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="moneta_sync", description="Google Sheet -> SQLite importer")
    p.add_argument("--sheet-id", default=os.environ.get("MONETA_SHEET_ID"), help="id from the sheet URL")
    p.add_argument("--worksheet", default=os.environ.get("MONETA_WORKSHEET", "inbox"))
    p.add_argument("--credentials", default=os.environ.get("MONETA_CREDENTIALS", "service_account.json"))
    p.add_argument("--db", default=os.environ.get("MONETA_DB", "moneta.db"))
    p.add_argument("--interval", type=int, default=0, help="seconds between runs; 0 = run once")
    a = p.parse_args(argv)
    if not a.sheet_id:
        p.error("--sheet-id (or MONETA_SHEET_ID) is required")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from .sheets import GoogleSheet  # imported here so tests do not need gspread

    conn = connect(a.db)
    sheet = GoogleSheet(a.sheet_id, a.worksheet, a.credentials)
    while True:
        r = import_once(sheet, conn)
        logging.info("read=%d inserted=%d duplicates=%d invalid=%d deleted=%d%s",
                     r.rows_read, r.inserted, r.duplicates, r.invalid, r.deleted,
                     f" ERROR={r.error}" if r.error else "")
        if not a.interval:
            return 1 if r.error else 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
