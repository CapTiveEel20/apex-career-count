"""Lines of the data files that cannot be used are warned about and kept as @BAD, never lost and never fatal."""
from apex.storage.account_file import account_path
from tests.helpers import SessionCase

JAN, FEB = "2025-01", "2025-02"
FOOTER = "# SUMMARY"
VIEWS = ("l", "k", "w", "g", "log", "report", "base", "account")


class MonthLineCase(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "7 1 wraith", "date 2025-02-10", "3 0 wraith")

    def add_line(self, line):
        self.write_month_text(FEB, self.month_text(FEB).replace(FOOTER, line + "\n" + FOOTER, 1))


class UnknownLineTests(MonthLineCase):
    def test_a_line_with_an_unknown_tag_is_warned_about_and_kept(self):
        line = "@NEW | future header | 1"
        self.add_line(line)
        _, warned = self.do_quietly("2 0 wraith")
        self.assertIn(line, warned)
        self.assertIn("@BAD", self.month_text(FEB))
        self.assertEqual(self.month_text(FEB).count(line), 1)

    def test_a_log_row_with_a_mistyped_tag_is_kept(self):
        line = "1 | 2025-02-10 10:00 | Wraith | 7 | 1"
        self.add_line(line)
        self.do_quietly("2 0 wraith")
        self.assertEqual(self.month_text(FEB).count(line), 1)

    def test_it_is_kept_by_every_later_save_exactly_once(self):
        line = "@NEW | future header | 1"
        self.add_line(line)
        self.do_quietly("2 0 wraith", "4 0 wraith", "undo")
        self.assertEqual(self.month_text(FEB).count(line), 1)

    def test_text_without_columns_is_not_data(self):
        self.add_line("a note to myself")
        out, warned = self.do_quietly("2 0 wraith")
        self.assertIn("SAVED", out)
        self.assertEqual(warned, "")

    def test_the_files_own_titles_and_comments_are_not_damaged(self):
        _, warned = self.do_quietly("account 100 10", "base wraith 500 50", "2 0 wraith", *VIEWS)
        self.assertEqual(warned, "")
        self.assertEqual(self.month(FEB).damaged, [])


class UnknownAccountLineTests(SessionCase):
    def test_a_line_with_an_unknown_tag_is_warned_about_and_kept(self):
        line = "@NEW | future header | 1"
        self.do("date 2025-01-10", "account 100 10")
        self.write_account_text(self.account_text() + line + "\n")
        _, warned = self.do_quietly("base wraith 500 50")
        self.assertIn(line, warned)
        self.assertIn("@BAD", self.account_text())
        self.assertEqual(self.account_text().count(line), 1)


class MalformedValueTests(MonthLineCase):
    LINES = ("@PREV | oops | 1 | 2 | 3",
             "@PL | oops | Wraith | 1 | 2 | 3",
             "@LV | oops | 700",
             "@LL | Wraith | oops",
             "@TK | oops | Wraith | 9 | 0",
             "@MB | oops | Wraith | 9 | 0",
             "@BU | 9 | oops | Wraith | 1 | 2 | x",
             "L | oops | Wraith | 1 | 2 | 0 | 9 | 0 | M")

    def test_a_bad_date_or_month_becomes_a_damaged_line_and_nothing_breaks(self):
        original = self.month_text(FEB)
        for line in self.LINES:
            with self.subTest(line=line):
                self.write_month_text(FEB, original)
                self.add_line(line)
                for view in VIEWS:
                    out, _ = self.do_quietly(view)
                    self.assertNotIn("does not match", out, view)
                    self.assertNotIn("unpack", out, view)
                out, warned = self.do_quietly("2 0 wraith")
                self.assertIn("SAVED", out)
                self.assertIn(line, warned)
                self.assertEqual(self.month_text(FEB).count(line), 1)

    def test_a_date_with_only_the_day_is_still_valid(self):
        self.add_line("@LL | Caustic | 2024-12-01")
        self.add_line("@LV | 2024-12-01 | 700")
        self.add_line("@TK | 2024-12-01 | Caustic | 9 | 0")
        _, warned = self.do_quietly("2 0 wraith")
        self.assertEqual(warned, "")
        self.assertEqual(self.month(FEB).ll["Caustic"], "2024-12-01")


class NotUtf8Tests(SessionCase):
    BAD_BYTES = b"\n# caf\xe9\n"

    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "account 100 10", "7 1 wraith")

    def spoil(self, path):
        with open(path, "ab") as f:
            f.write(self.BAD_BYTES)
        with open(path, "rb") as f:
            return f.read()

    def assert_named_error(self, out, name):
        self.assertIn(name, out)
        self.assertIn("UTF-8", out)
        self.assertNotIn("codec", out)

    def test_a_monthly_file_names_itself_and_is_left_alone(self):
        path = self.month_file(JAN)
        before = self.spoil(path)
        self.assert_named_error(self.do("l"), f"apex_stats_{JAN}.txt")
        self.assert_named_error(self.do("2 0 wraith"), f"apex_stats_{JAN}.txt")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_the_account_file_names_itself_and_is_left_alone(self):
        path = account_path(self.d)
        before = self.spoil(path)
        self.assert_named_error(self.do("base"), "account_stats.txt")
        self.assert_named_error(self.do("2 0 wraith"), "account_stats.txt")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before)
