"""At the start of a month, before its first record: the views already show the new month, and a month
with damaged lines is not rolled over, so its totals are never left out of the next one."""
import os
from datetime import date

from apex.core.records import Tally
from tests.helpers import SessionCase

JAN, FEB = "2025-01", "2025-02"
TODAY = date.today().strftime("%Y-%m")


def legend_row(text, legend):
    line = next(x for x in text.splitlines() if x.startswith(legend))
    return [c.strip() for c in line.split("|")][1:]


class NewMonthViewTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "base wraith 100 10", "7 1 wraith")

    def test_k_and_w_show_todays_month_with_nothing_in_it_yet(self):
        out = self.do("k")
        self.assertIn(f"current month: {TODAY}", out)
        self.assertEqual(legend_row(out, "Wraith"), ["0", "0", "0", "107"])
        self.assertEqual(legend_row(self.do("w"), "Wraith"), ["0", "0", "0", "11"])

    def test_l_shows_todays_month_with_no_kills_yet(self):
        out = self.do("l")
        self.assertIn(f"TOP 3 THIS MONTH  ({TODAY})", out)
        self.assertIn("(no kills this month)", out)
        self.assertEqual(legend_row(out, "Wraith")[:2], ["107", "11"])
        self.assertIn("2025-01-10", legend_row(out, "Wraith")[2])

    def test_g_shows_todays_month_and_the_closed_months_best(self):
        out = self.do("g")
        self.assertIn(f"GAMES THIS MONTH  ({TODAY})", out)
        self.assertIn("Jan 2025", out)

    def test_the_views_write_nothing(self):
        before = (sorted(os.listdir(self.d)), self.month_text(JAN))
        self.do("l", "k", "w", "g", "log", "report")
        self.assertEqual((sorted(os.listdir(self.d)), self.month_text(JAN)), before)

    def test_the_first_record_of_the_month_shows_in_it(self):
        out = self.do("date today", "3 0 octane", "k")
        self.assertIn(f"current month: {TODAY}", out)
        self.assertEqual(legend_row(out, "Octane")[0], "3")


class ReportLabelTests(SessionCase):
    def test_the_last_row_says_it_counts_what_was_logged(self):
        out = self.do("account 15000 900", "7 1", "report")
        self.assertNotIn("ALL-TIME", out)
        self.assertEqual(sum(x.startswith("ALL LOGGED") for x in out.splitlines()), 1)


class DamagedRolloverTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "7 1 wraith", "12 0 octane")
        self.original = self.month_text(JAN)
        lines = self.original.split("\n")
        i = next(i for i, x in enumerate(lines) if x.startswith("L ") and "Wraith" in x)
        cells = lines[i].split("|")
        cells[3] = " x "
        lines[i] = "|".join(cells)
        self.damaged = "\n".join(lines)
        self.write_month_text(JAN, self.damaged)

    def test_the_first_record_of_the_next_month_is_refused(self):
        out, _ = self.do_quietly("date 2025-02-10", "3 0 wraith")
        self.assertIn("apex_stats_2025-01.txt has damaged lines", out)
        self.assertIn("Nothing was saved", out)
        self.assertFalse(self.has_month(FEB))
        self.assertEqual(self.month_text(JAN), self.damaged)

    def test_once_fixed_the_whole_month_carries_over(self):
        self.do_quietly("date 2025-02-10", "3 0 wraith")
        self.write_month_text(JAN, self.original)
        self.assertIn("SAVED", self.do("3 0 wraith"))
        self.assertEqual(self.month(FEB).hist, Tally(2, 19, 1))

    def test_the_damaged_month_itself_still_takes_records(self):
        out, _ = self.do_quietly("5 0 wraith")
        self.assertIn("SAVED", out)
        self.assertFalse(self.has_month(FEB))
