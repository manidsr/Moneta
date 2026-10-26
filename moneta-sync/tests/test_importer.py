import unittest
from moneta_sync.db import connect
from moneta_sync.importer import SheetRow, import_once, norm_text, parse_date_ms, parse_row


def row(_uid, **kw):
    r = dict(uid=_uid, date="2026-10-20T14:30:00+03:30", type="expense", amount=250000,
             description="Snapp", balance=1750000, ref="R1", raw="sms text")
    r.update(kw)
    return r


class FakeSheet:
    """In-memory stand-in for the Google Sheet."""
    def __init__(self, rows):
        self.rows = [dict(r) for r in rows]
        self.fail_delete = False
        self.after_read = None

    def read_rows(self):
        snap = [SheetRow(i + 2, dict(r)) for i, r in enumerate(self.rows)]
        if self.after_read:
            self.after_read(self)  # e.g. the phone appends a row mid-run
        return snap

    def delete_rows_by_uid(self, uids):
        if self.fail_delete:
            raise RuntimeError("quota exceeded")
        before = len(self.rows)
        self.rows = [r for r in self.rows if norm_text(r.get("uid")) not in uids]
        return before - len(self.rows)


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def count(self):
        return self.db.execute("select count(*) from transactions").fetchone()[0]

    def test_imports_then_clears_sheet(self):
        sh = FakeSheet([row("a"), row("b", type="income", amount=48000000)])
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.duplicates, r.invalid, r.deleted, r.error), (2, 0, 0, 2, None))
        self.assertEqual(sh.rows, [])
        self.assertEqual(self.count(), 2)
        st, src = self.db.execute("select st, src from transactions").fetchone()
        self.assertEqual((st, src), ("review", "sms"))

    def test_rerun_never_duplicates(self):
        import_once(FakeSheet([row("a")]), self.db)
        sh = FakeSheet([row("a")])  # phone re-sent the same SMS
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.duplicates, r.deleted), (0, 1, 1))
        self.assertEqual(self.count(), 1)
        self.assertEqual(sh.rows, [])

    def test_same_uid_twice_in_one_batch(self):
        sh = FakeSheet([row("a"), row("a")])
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.duplicates, r.deleted), (1, 1, 2))

    def test_invalid_rows_stay_in_sheet(self):
        sh = FakeSheet([row("good"), row("bad1", amount="abc"), row("bad2", type="refund"), row("bad3", uid="")])
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.invalid, r.deleted), (1, 3, 1))
        self.assertEqual([x["uid"] for x in sh.rows], ["bad1", "bad2", ""])

    def test_delete_failure_loses_nothing_and_recovers(self):
        sh = FakeSheet([row("a"), row("b")])
        sh.fail_delete = True
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.deleted), (2, 0))
        self.assertIn("quota", r.error)
        self.assertEqual(len(sh.rows), 2)  # still in the sheet, also safe in the DB
        sh.fail_delete = False
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.duplicates, r.deleted, r.error), (0, 2, 2, None))
        self.assertEqual(self.count(), 2)
        self.assertEqual(sh.rows, [])

    def test_row_added_during_run_is_not_deleted(self):
        sh = FakeSheet([row("a")])
        sh.after_read = lambda s: s.rows.append(row("late"))
        import_once(sh, self.db)
        self.assertEqual([x["uid"] for x in sh.rows], ["late"])
        sh.after_read = None
        r = import_once(sh, self.db)
        self.assertEqual((r.inserted, r.deleted), (1, 1))
        self.assertEqual(self.count(), 2)

    def test_sheet_failure_is_reported_not_raised(self):
        class Broken:
            def read_rows(self): raise RuntimeError("offline")
            def delete_rows_by_uid(self, u): return 0
        r = import_once(Broken(), self.db)
        self.assertIn("offline", r.error)
        self.assertEqual(self.db.execute("select count(*) from sync_runs").fetchone()[0], 1)

    def test_value_parsing(self):
        ms = 1792494000000
        self.assertEqual(parse_date_ms(ms), ms)
        self.assertEqual(parse_date_ms(float(ms)), ms)
        self.assertEqual(parse_date_ms(str(ms)), ms)
        self.assertEqual(parse_date_ms(ms // 1000), ms)
        self.assertEqual(parse_date_ms("2026-10-20T14:30:00+03:30"), ms)
        self.assertEqual(parse_date_ms("2026-10-20T11:00:00Z"), ms)
        with self.assertRaises(ValueError):
            parse_date_ms("yesterday")
        t = parse_row(row("x", amount="۲۵۰٬۰۰۰", balance="1,750,000.0"))
        self.assertEqual((t.amount, t.balance), (250000, 1750000))
        self.assertEqual(parse_row(row("x", balance="")).balance, None)
        self.assertEqual(parse_row(row(12345.0)).uid, "12345")


if __name__ == "__main__":
    unittest.main()
