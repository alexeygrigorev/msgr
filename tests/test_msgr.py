import tempfile
import unittest
from pathlib import Path

from msgr import adb, store

SAMPLE = (
    "Row: 0 _id=7, address=+4912345678, date=1700000000000, body=plain text\n"
    "Row: 1 _id=8, address=Sender, date=1700000001000, body=has, commas = and\n"
    "Row: 2 _id=9, address=Telegram, date=1700000002000, body=line one\n"
    "line two, still id 9\n"
    "Row: 3 _id=10, address=+4987654321, date=1700000003000, body=fake marker\n"
    "Row: 9 _id=11, address=X, date=1700000004000, body=not a new row\n"
)


class ParseTest(unittest.TestCase):
    def test_parse_rows(self):
        msgs = adb.parse_rows(SAMPLE)
        self.assertEqual([m["id"] for m in msgs], [7, 8, 9, 10, 11])
        self.assertEqual(msgs[1]["body"], "has, commas = and")
        self.assertEqual(msgs[2]["body"], "line one\nline two, still id 9")
        # a body line shaped exactly like a Row: header starts a new row —
        # content query output has no escaping, so that boundary is ambiguous
        self.assertEqual(msgs[3]["body"], "fake marker")
        self.assertEqual(msgs[4]["body"], "not a new row")
        self.assertEqual(msgs[0]["date_ms"], 1700000000000)

    def test_empty(self):
        self.assertEqual(adb.parse_rows(""), [])


class StoreTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            con = store.connect(str(Path(tmp) / "t.db"))
            msgs = adb.parse_rows(SAMPLE)
            self.assertEqual(store.upsert(con, "dev", msgs), 5)
            self.assertEqual(store.upsert(con, "dev", msgs), 0)  # dedupe
            self.assertEqual(len(store.list_messages(con, "new")), 5)
            row = store.get_message(con, 8)
            self.assertEqual(row["address"], "Sender")
            store.mark_read(con, row)
            self.assertEqual(len(store.list_messages(con, "new")), 4)
            self.assertEqual(len(store.list_messages(con, "archived")), 1)
            self.assertEqual(store.get_message(con, 8)["state"], "archived")
            store.set_state(con, 8, "new")
            self.assertEqual(len(store.list_messages(con, "new")), 5)
            con.close()

    def test_fmt_ts(self):
        self.assertEqual(store.fmt_ts(1700000000000), "2023-11-14 23:13")


if __name__ == "__main__":
    unittest.main()
