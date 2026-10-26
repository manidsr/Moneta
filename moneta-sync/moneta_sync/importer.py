"""Pull rows from the Google Sheet inbox into SQLite, then remove them from the sheet.

Safety rules:
  * a row is deleted from the sheet only AFTER the database transaction has committed;
  * the database ignores a uid it already has, so re-running is always harmless;
  * invalid rows are left in the sheet (and logged) so they can be fixed by hand.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

log = logging.getLogger("moneta_sync")

REQUIRED_COLUMNS = ("uid", "date", "type", "amount", "description")
# optional sheet columns: balance, ref, raw
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class SheetError(Exception):
    """The sheet is missing, unreadable, or has the wrong header."""


@dataclass(frozen=True)
class SheetRow:
    row_number: int  # 1-based row number in the sheet (header is row 1)
    values: dict[str, Any]  # keyed by lower-case header name


class Sheet(Protocol):
    def read_rows(self) -> list[SheetRow]: ...

    def delete_rows_by_uid(self, uids: set[str]) -> int:
        """Delete every data row whose uid is in `uids`. Returns rows deleted."""


@dataclass(frozen=True)
class Transaction:
    uid: str
    date: int
    type: str
    amount: int
    description: str
    balance: int | None
    ref: str | None
    raw: str | None


@dataclass
class RunResult:
    rows_read: int = 0
    inserted: int = 0
    duplicates: int = 0
    invalid: int = 0
    deleted: int = 0
    error: str | None = None


# ---------------------------------------------------------------- parsing

def norm_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def parse_int(v: Any, field: str) -> int:
    if isinstance(v, bool):
        raise ValueError(f"{field}: not a whole number: {v!r}")
    if isinstance(v, (int, float)):
        if float(v) != int(v):
            raise ValueError(f"{field}: not a whole number: {v!r}")
        return int(v)
    s = norm_text(v).translate(_DIGITS).replace(",", "").replace("٬", "")
    if not re.fullmatch(r"-?\d+(\.0+)?", s):
        raise ValueError(f"{field}: not a whole number: {v!r}")
    return int(s.split(".")[0])


def parse_date_ms(v: Any) -> int:
    """Accepts epoch ms, epoch seconds, or an ISO-8601 string. Returns epoch ms."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        n = int(v)
    else:
        s = norm_text(v).translate(_DIGITS)
        if re.fullmatch(r"\d+", s):
            n = int(s)
        else:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"date: not a valid date: {v!r}") from None
            return int(dt.astimezone().timestamp() * 1000)  # naive = local time
    if n < 10**11:  # looks like seconds
        n *= 1000
    if not (946_684_800_000 <= n <= 4_102_444_800_000):  # years 2000..2100
        raise ValueError(f"date: out of range: {v!r}")
    return n


def parse_row(values: dict[str, Any]) -> Transaction:
    missing = [c for c in REQUIRED_COLUMNS if norm_text(values.get(c)) == ""]
    if missing:
        raise ValueError("missing " + ", ".join(missing))
    typ = norm_text(values["type"]).lower()
    if typ not in ("income", "expense"):
        raise ValueError(f"type: must be income or expense, got {values['type']!r}")
    amount = parse_int(values["amount"], "amount")
    if amount <= 0:
        raise ValueError("amount: must be greater than zero")
    bal = values.get("balance")
    return Transaction(
        uid=norm_text(values["uid"]),
        date=parse_date_ms(values["date"]),
        type=typ,
        amount=amount,
        description=norm_text(values["description"]),
        balance=parse_int(bal, "balance") if norm_text(bal) != "" else None,
        ref=norm_text(values.get("ref")) or None,
        raw=norm_text(values.get("raw")) or None,
    )


# ---------------------------------------------------------------- import

_INSERT = """
INSERT OR IGNORE INTO transactions
    (uid, date, type, amount, description, ref, bal, src, st, raw, created)
VALUES (?, ?, ?, ?, ?, ?, ?, 'sms', 'review', ?, ?)
"""


def import_once(sheet: Sheet, conn: sqlite3.Connection, now_ms: int | None = None) -> RunResult:
    now_ms = now_ms or int(time.time() * 1000)
    res = RunResult()
    try:
        rows = sheet.read_rows()
        res.rows_read = len(rows)

        valid: list[Transaction] = []
        for r in rows:
            try:
                valid.append(parse_row(r.values))
            except (ValueError, OverflowError) as e:
                res.invalid += 1
                log.warning("sheet row %d skipped: %s", r.row_number, e)

        with conn:  # one transaction: all valid rows are saved, or none
            for t in valid:
                cur = conn.execute(
                    _INSERT,
                    (t.uid, t.date, t.type, t.amount, t.description, t.ref, t.balance, t.raw, now_ms),
                )
                res.inserted += cur.rowcount
        res.duplicates = len(valid) - res.inserted

        # Only reached after the commit above. If this fails, the rows stay in the
        # sheet and the next run skips them as duplicates and retries the delete.
        if valid:
            res.deleted = sheet.delete_rows_by_uid({t.uid for t in valid})
    except Exception as e:  # noqa: BLE001 - a bad run must never kill the loop
        res.error = f"{type(e).__name__}: {e}"
        log.exception("sync run failed")

    try:
        with conn:
            conn.execute(
                "INSERT INTO sync_runs (ran_at, rows_read, inserted, duplicates, invalid, deleted, error) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now_ms, res.rows_read, res.inserted, res.duplicates, res.invalid, res.deleted, res.error),
            )
    except sqlite3.Error:
        log.exception("could not write sync_runs")
    return res
