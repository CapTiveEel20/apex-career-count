import os
import re
import unittest
from unittest.mock import patch

from apex.core.aggregates import monthly_bests, top_matches
from apex.core.records import Entry, Tally, TopMatch
from apex.display.colors import GREEN, RED
from apex.storage.monthly_file import parse, render
from tests.helpers import SessionCase

JAN, FEB = "2025-01", "2025-02"


def best(kills, month):
    return TopMatch(f"2024-{month:02}-01 10:00", "Old", kills, 0)


def match(kills, day="2025-03-01 10:00", wins=0, src="M", id_=1):
    return Entry(day, "New", kills, wins, 0, id_, 0, src)


class TopMatchesTests(unittest.TestCase):
    def test_ranks_by_kills_and_ignores_wins(self):
        logs = [match(5, wins=1), match(9), match(7, wins=3)]
        self.assertEqual([r.kills for r in top_matches([], logs)], [9, 7, 5])

    def test_ties_keep_the_earlier_match_first(self):
        logs = [match(7, "2025-03-02 10:00", wins=1), match(7, "2025-03-01 10:00")]
        self.assertEqual([r.date for r in top_matches([], logs)], ["2025-03-01 10:00", "2025-03-02 10:00"])

    def test_only_matches_with_kills_count(self):
        logs = [match(0, wins=1), match(50, src="A"), match(60, src="B")]
        self.assertEqual(top_matches([], logs), [])


class MonthlyBestsTests(unittest.TestCase):
    FULL = [best(k, i + 1) for i, k in enumerate((30, 25, 20, 15, 10, 5))]

    def test_joins_while_there_is_room(self):
        short = self.FULL[:2]
        self.assertEqual([r.kills for r in monthly_bests(short, [match(1)])], [30, 25, 1])

    def test_replaces_the_lowest_when_it_beats_it(self):
        got = monthly_bests(self.FULL, [match(6)])
        self.assertEqual([r.kills for r in got], [30, 25, 20, 15, 10, 6])
        self.assertEqual(got[-1].legend, "New")

    def test_equal_to_the_lowest_does_not_get_in(self):
        self.assertEqual(monthly_bests(self.FULL, [match(5)]), self.FULL)

    def test_a_month_with_no_matches_changes_nothing(self):
        self.assertEqual(monthly_bests(self.FULL, []), self.FULL)

    def test_only_the_months_top_match_is_taken(self):
        got = monthly_bests([], [match(3), match(8)])
        self.assertEqual([r.kills for r in got], [8])


class RolloverTests(SessionCase):
    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "7 1 wraith", "12 0 octane")

    def roll(self):
        self.do("date 2025-02-01", "3 0 wraith")

    def test_totals_are_carried_and_the_log_starts_empty(self):
        self.roll()
        feb = self.month(FEB)
        self.assertEqual(feb.hist, Tally(2, 19, 1))
        self.assertEqual(feb.prev, [(JAN, Tally(2, 19, 1))])
        self.assertEqual(feb.hl["Wraith"], Tally(1, 7, 1))
        self.assertEqual(len(feb.logs), 1)

    def test_the_previous_file_is_untouched(self):
        before = self.month_text(JAN)
        self.roll()
        self.assertEqual(self.month_text(JAN), before)

    def test_carries_the_top_matches_and_stores_the_months_best(self):
        self.roll()
        feb = self.month(FEB)
        self.assertEqual([r.kills for r in feb.top], [12, 7])
        self.assertEqual([(r.kills, r.legend) for r in feb.bests], [(12, "Octane")])

    def test_each_closed_month_adds_one_best(self):
        self.roll()
        self.do("date 2025-03-01", "1 0 wraith")
        self.assertEqual([r.kills for r in self.month("2025-03").bests], [12, 3])

    def test_account_and_base_gains_are_not_matches(self):
        self.do("account 100 10", "account 500 10", "base lifeline 10 1", "base lifeline 900 1")
        self.roll()
        feb = self.month(FEB)
        self.assertEqual([r.kills for r in feb.top], [12, 7])
        self.assertEqual([r.kills for r in feb.bests], [12])

    def test_undoing_the_first_record_of_a_month_goes_back_to_the_previous_one(self):
        self.roll()
        self.do("undo")
        self.assertFalse(self.has_month(FEB))
        self.assertEqual(len(self.month(JAN).logs), 2)
        self.assertEqual(self.month(JAN).bests, [])

    def test_a_closed_month_takes_no_new_entries(self):
        self.roll()
        self.assertIn("already closed", self.do("date 2025-01-20", "5 0 wraith"))
        self.assertEqual(len(self.month(JAN).logs), 2)

    def test_a_rolled_over_file_reads_back_the_same(self):
        self.do("accountl 700", "account 100 10", "base wraith 50 5")
        self.roll()
        self.do("base wraith 60 5")
        feb = self.month(FEB)
        self.assertEqual(parse(render(FEB, feb)), feb)


class DamagedMonthTests(SessionCase):
    BROKEN = "L | 2025-01-10 10:00 | Wraith | x | 1"

    def test_a_damaged_line_is_warned_about_and_kept(self):
        self.do("date 2025-01-10", "7 1 wraith")
        text = self.month_text(JAN)
        self.write_month_text(JAN, text.replace("# SUMMARY", self.BROKEN + "\n# SUMMARY", 1))
        _, warned = self.do_quietly("3 0 wraith")
        self.assertIn(self.BROKEN, warned)
        self.assertEqual(self.month_text(JAN).count(self.BROKEN), 1)
        self.do_quietly("2 0 wraith")
        self.assertEqual(self.month_text(JAN).count(self.BROKEN), 1)


class GamesViewTests(SessionCase):
    @staticmethod
    def rows(out):
        """Cells of the left table's numbered rows."""
        lines = [x for x in out.split("\n")[3:] if x[:2].strip().isdigit()]
        return [re.split(r"\s*\|\s*", x) for x in lines]

    def test_ranks_this_month_by_kills_and_shows_the_win(self):
        self.do("7 wraith", "7", "12 1 bloodhound", "0 1 lifeline")
        rows = self.rows(self.do("g"))
        self.assertEqual([(r[1], r[2]) for r in rows], [("12", "W"), ("7", "W"), ("7", "L")])

    def test_legends_are_not_colored_but_kills_and_wins_are(self):
        self.do("7 1 wraith")
        with patch("apex.display.colors.COLOR", True):
            row = next(x for x in self.do("g").split("\n") if "Wraith" in x)
        self.assertIn(f" | {'Wraith':<12} | ", row)
        self.assertIn(RED, row)
        self.assertIn(GREEN + "W", row)

    def test_shows_at_most_ten_games(self):
        self.do(*[f"{n} 0 horizon" for n in range(1, 13)])
        rows = self.rows(self.do("g"))
        self.assertEqual([r[1] for r in rows], [str(n) for n in range(12, 2, -1)])

    def test_a_past_month_shows_as_closed_and_writes_nothing(self):
        self.do("date 2025-01-10", "9 1 caustic")
        before = (sorted(os.listdir(self.d)), self.month_text(JAN))
        out = self.do("g")
        self.assertIn("(no matches with kills this month)", out)
        self.assertIn("Jan 2025", out)
        self.assertEqual((sorted(os.listdir(self.d)), self.month_text(JAN)), before)

    def test_every_table_line_has_the_same_right_edge(self):
        self.do("date 2025-01-10", "9 1 caustic", "date 2025-02-01", "9 1 caustic", "date today", "3 0 wraith")
        lines = [x for x in self.do("g").split("\n")[1:] if x]
        self.assertEqual(len({len(x) for x in lines}), 1, lines)


if __name__ == "__main__":
    unittest.main()
