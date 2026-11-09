import os
import tempfile
import unittest
from unittest.mock import patch

from apex.storage.account_file import load_acct
from apex.storage.atomic import TMP, FileChange, commit_files
from tests.helpers import SessionCase

REAL_REPLACE = os.replace


class CommitFilesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.first = os.path.join(tmp.name, "first.txt")
        self.second = os.path.join(tmp.name, "second.txt")
        with open(self.first, "w", encoding="utf-8") as f:
            f.write("old first")
        self.changes = [FileChange(self.first, "new first", "old first"), FileChange(self.second, "new second", None)]

    @staticmethod
    def read(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_writes_every_file(self):
        commit_files(self.changes)
        self.assertEqual(self.read(self.first), "new first")
        self.assertEqual(self.read(self.second), "new second")
        self.assertFalse(os.path.exists(self.first + TMP))

    def test_a_failed_swap_puts_the_earlier_files_back(self):
        def fail_second(src, dst):
            if dst == self.second:
                raise OSError("locked")
            REAL_REPLACE(src, dst)

        with patch("apex.storage.atomic.os.replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                commit_files(self.changes)
        self.assertEqual(self.read(self.first), "old first")
        self.assertFalse(os.path.exists(self.second))
        self.assertFalse(os.path.exists(self.first + TMP))
        self.assertFalse(os.path.exists(self.second + TMP))

    def test_each_file_reaches_the_disk_before_it_is_swapped_in(self):
        calls = []
        real_fsync = os.fsync

        def fsync(fd):
            calls.append("fsync")
            real_fsync(fd)

        def replace(src, dst):
            calls.append("replace")
            REAL_REPLACE(src, dst)

        with patch("apex.storage.atomic.os.fsync", side_effect=fsync), \
                patch("apex.storage.atomic.os.replace", side_effect=replace):
            commit_files(self.changes)
        self.assertEqual(calls, ["fsync", "fsync", "replace", "replace"])


class DamagedAccountFileTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "account 1000 100", "base wraith 500 50", "base octane 300 30")

    def damage(self, old, new):
        text = self.account_text()
        self.assertIn(old, text)
        self.write_account_text(text.replace(old, new, 1))

    def test_a_damaged_base_is_warned_about_and_survives_saves(self):
        self.damage(" 300 |", " 3OO |")
        _, warned = self.do_quietly("7 1 wraith")
        self.assertIn("3OO", warned)
        self.do_quietly("2 0 wraith")
        text = self.account_text()
        self.assertEqual(text.count("3OO"), 1)
        self.assertIn("@BAD", text)
        self.assertNotIn("Octane", self.quiet_bases())

    def test_the_rest_of_the_file_keeps_working_with_a_damaged_base(self):
        self.damage(" 300 |", " 3OO |")
        self.do_quietly("7 1 wraith")
        data = self.quiet_load()
        self.assertEqual(data.account.kills, 1007)
        self.assertEqual(data.bases["Wraith"].kills, 500)

    def test_a_fixed_line_counts_again(self):
        self.damage(" 300 |", " 3OO |")
        self.do_quietly("7 1 wraith")
        lines = [x for x in self.account_text().split("\n") if not x.startswith("@BAD")]
        fixed = f"{'@BASE':<9} | {'Octane':<12} | {300:>10} | {30:>10} | 2025-01-10 10:00"
        self.write_account_text("\n".join(lines + [fixed]) + "\n")
        self.assertEqual(self.bases()["Octane"].kills, 300)

    def test_a_damaged_account_line_blocks_saves_and_changes_nothing(self):
        self.damage(" 1000 |", " 1OOO |")
        before = self.account_text()
        logs_before = len(self.month("2025-01").logs)
        for line in ("7 1 wraith", "account 50 5", "base wraith 600 50"):
            out, _ = self.do_quietly(line)
            self.assertIn("is damaged", out)
        self.assertEqual(self.asked, 0)
        self.assertEqual(self.account_text(), before)
        self.assertEqual(len(self.month("2025-01").logs), logs_before)

    def test_an_account_line_with_missing_columns_is_damaged_too(self):
        self.write_account_text("@ACCOUNT | 12\n")
        data = self.quiet_load()
        self.assertTrue(data.account_damaged)
        self.assertIsNone(data.account)

    def test_views_still_open_with_a_damaged_account_line(self):
        self.damage(" 1000 |", " 1OOO |")
        out, warned = self.do_quietly("k")
        self.assertIn("BY LEGEND", out)
        self.assertIn("1OOO", warned)

    def quiet_load(self):
        with patch("sys.stderr"):
            return load_acct(self.d)

    def quiet_bases(self):
        return self.quiet_load().bases


class MissingAccountFileTests(SessionCase):
    def test_a_missing_file_is_simply_not_set(self):
        data = load_acct(self.d)
        self.assertIsNone(data.account)
        self.assertEqual(data.bases, {})
        self.assertEqual(data.damaged, [])


if __name__ == "__main__":
    unittest.main()
