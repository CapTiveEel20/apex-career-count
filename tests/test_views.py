"""The read-only views that depend on history: report, the l family, w, the base listing."""
from datetime import date, timedelta

from tests.helpers import SessionCase

WEEK, MONTH, QUARTER, HALF, YEAR, ALL = "1 WEEK", "1 MONTH", "3 MONTHS", "6 MONTHS", "1 YEAR", "ALL LOGGED"


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def report_row(text, label):
    """(kills, wins, levels gained) of a 'report' row: the two tables share each line."""
    line = next(x for x in text.splitlines() if x.startswith(label))
    cells = [c.strip() for c in line.split("|")]
    return tuple(int(c.replace(",", "")) for c in (cells[2], cells[3].split()[0], cells[-1]))


class ReportTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do(f"date {days_ago(400)}", "accountl 100", "10 1 wraith",
                f"date {days_ago(100)}", "5l", "20 0 octane",
                f"date {days_ago(20)}", "40 2 wraith",
                f"date {days_ago(3)}", "3l", "5 1 wraith",
                "date today", "1 0 octane")

    def test_each_window_adds_up_entries_from_every_month(self):
        out = self.do("report")
        got = {label: report_row(out, label)[:2] for label in (WEEK, MONTH, QUARTER, HALF, YEAR, ALL)}
        self.assertEqual(got, {WEEK: (6, 1), MONTH: (46, 3), QUARTER: (46, 3), HALF: (66, 3), YEAR: (66, 3), ALL: (76, 4)})

    def test_levels_gained_start_from_the_last_level_before_each_window(self):
        out = self.do("report")
        got = {label: report_row(out, label)[2] for label in (WEEK, MONTH, QUARTER, HALF, YEAR, ALL)}
        self.assertEqual(got, {WEEK: 3, MONTH: 3, QUARTER: 3, HALF: 8, YEAR: 8, ALL: 8})

    def test_shows_the_current_level(self):
        self.assertIn("current: Level 108 Tier 1", self.do("report"))


class ReportEdgeTests(SessionCase):
    def test_an_entry_on_the_from_day_is_outside_the_window(self):
        self.do(f"date {days_ago(7)}", "9 1 wraith", "date today", "1 0 wraith")
        out = self.do("report")
        self.assertEqual(report_row(out, WEEK)[:2], (1, 0))
        self.assertEqual(report_row(out, MONTH)[:2], (10, 1))

    def test_no_levels_recorded_gains_nothing(self):
        self.do("date today", "1 0 wraith")
        self.assertEqual(report_row(self.do("report"), ALL)[2], 0)

    def test_no_data_yet(self):
        self.assertIn("No data recorded yet", self.do("report"))


class LegendViewTests(SessionCase):
    NAMES = ("Wraith", "Octane", "Caustic", "Newcomer")

    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "base wraith 100 10", "base octane 50 40", "base caustic 70 1",
                "3 1 wraith", "date 2025-01-11", "5 0 octane", "1 0 newcomer")

    def left(self, line):
        """The legends of the left table, in order (the right table shares its lines, after a rank)."""
        cells = [x.split("|")[0].strip() for x in self.do(line).splitlines()]
        return [c for c in cells if c in self.NAMES]

    def test_l_sorts_by_all_time_kills(self):
        self.assertEqual(self.left("l"), ["Wraith", "Caustic", "Octane"])

    def test_lw_sorts_by_all_time_wins(self):
        self.assertEqual(self.left("lw"), ["Octane", "Wraith", "Caustic"])

    def test_la_sorts_by_name(self):
        self.assertEqual(self.left("la"), ["Caustic", "Octane", "Wraith"])

    def test_lm_puts_the_most_recent_first_and_never_played_last(self):
        self.assertEqual(self.left("lm"), ["Octane", "Wraith", "Caustic"])

    def test_ls_filters_the_left_table_in_any_case(self):
        self.assertEqual(self.left("ls WRA"), ["Wraith"])

    def test_ls_does_not_filter_the_top_3(self):
        out = self.do("date today", "5 0 octane", "ls wra")
        self.assertIn("| Octane", out)

    def test_ls_with_no_match(self):
        self.assertIn("(no base legend matches 'zzz')", self.do("ls zzz"))

    def test_ls_needs_a_name(self):
        self.assertIn("APEX CAREER COUNT", self.do("ls"))

    def test_only_base_legends_are_on_the_left(self):
        self.assertNotIn("Newcomer", self.left("l"))

    def test_shows_all_time_totals_and_the_last_match(self):
        line = next(x for x in self.do("l").splitlines() if x.startswith("Octane"))
        cells = [c.strip() for c in line.split("|")]
        self.assertEqual(cells[1:3], ["55", "40"])
        self.assertTrue(cells[3].startswith("2025-01-11"))

    def test_never_played_shows_a_dash(self):
        line = next(x for x in self.do("l").splitlines() if x.startswith("Caustic"))
        self.assertEqual([c.strip() for c in line.split("|")][3].split()[0], "-")


class OtherViewTests(SessionCase):
    def test_w_lists_wins_with_a_grand_total(self):
        self.do("date 2025-01-10", "base wraith 100 10", "3 2 wraith", "1 1 octane")
        out = self.do("w")
        self.assertIn("# WINS BY LEGEND", out)
        total = next(x for x in out.splitlines() if x.startswith("GRAND TOTAL"))
        self.assertEqual(total.split("|")[-1].strip(), "13")

    def test_base_lists_all_time_totals(self):
        self.do("date 2025-01-10", "base wraith 100 10", "3 2 wraith")
        line = next(x for x in self.do("base").splitlines() if x.startswith("Wraith"))
        self.assertEqual([c.strip() for c in line.split("|")][1:], ["103", "12"])

    def test_base_with_none_set(self):
        self.assertIn("no bases set yet", self.do("base"))

    def test_a_level_above_a_later_one_is_refused(self):
        self.do("date 2025-01-20", "accountl 500", "date 2025-01-10")
        self.assertIn("recorded later", self.do("accountl 600"))
        self.assertEqual([e.level for e in self.month("2025-01").logs], [500])
