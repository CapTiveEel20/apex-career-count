"""The first 'account' and the first 'base' of each legend are a starting point: only later gains count."""
from datetime import date

from apex.ui.menus import quick_guide
from tests.helpers import SessionCase
from tests.test_views import ALL, HALF, MONTH, QUARTER, WEEK, YEAR, report_row

WINDOWS = (WEEK, MONTH, QUARTER, HALF, YEAR, ALL)


def legend_row(text, legend):
    line = next(x for x in text.splitlines() if x.startswith(legend))
    return [c.strip() for c in line.split("|")][1:]


class FirstTotalsTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("account 15000 900", "base wraith 3000 150", "base octane 2000 100")

    def logs(self):
        return self.month(date.today().strftime("%Y-%m")).logs

    def test_nothing_is_logged(self):
        self.assertEqual(self.logs(), [])

    def test_they_are_not_in_the_report(self):
        out = self.do("report")
        self.assertEqual({label: report_row(out, label)[:2] for label in WINDOWS}, {label: (0, 0) for label in WINDOWS})

    def test_they_are_not_in_the_period_columns(self):
        self.assertEqual(legend_row(self.do("k"), "Wraith")[:3], ["0", "0", "0"])
        self.assertEqual(legend_row(self.do("w"), "Wraith")[:3], ["0", "0", "0"])

    def test_they_are_not_in_the_top_3_games_or_log(self):
        self.assertIn("(no kills this month)", self.do("l"))
        self.assertIn("(no matches with kills this month)", self.do("g"))
        self.assertIn("(no matches logged this month)", self.do("log"))

    def test_they_stay_the_legends_all_time_totals(self):
        self.assertEqual(legend_row(self.do("l"), "Wraith")[:2], ["3,000", "150"])

    def test_a_new_legends_first_base_moves_nothing_later_on(self):
        self.do("base wraith 3050 155", "base caustic 70 1")
        self.assertEqual([(e.legend, e.kills) for e in self.logs()], [("Wraith", 50)])
        self.assertEqual((self.account().kills, self.account().wins), (15050, 905))


class SecondTimeTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("account 15000 900", "base wraith 3000 150", "base wraith 3050 155", "account 15100 910")

    def test_both_gains_are_in_the_report(self):
        self.assertEqual(report_row(self.do("report"), WEEK)[:2], (100, 10))

    def test_the_base_gain_is_in_the_period_columns(self):
        self.assertEqual(legend_row(self.do("k"), "Wraith")[:3], ["50", "50", "50"])


class MenuTests(SessionCase):
    def test_log_is_listed_with_the_tables_inside_the_ui_width(self):
        lines = [x for x in quick_guide().splitlines() if "| log" in x]
        self.assertEqual(len(lines), 1)
        self.assertLessEqual(len(lines[0]), 79)
        self.assertIn("(By Period) | log", lines[0])
