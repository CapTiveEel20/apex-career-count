import os
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from apex.config import ABORTED, SRC_ACCOUNT, SRC_BASE, SRC_MATCH
from apex.display.colors import green, red
from apex.ui.menus import help_text, quick_guide
from apex.ui.repl import confirm_new_legend
from tests.helpers import SessionCase

JAN = "2025-01"


class DatedCase(SessionCase):
    """Every entry is saved in January 2025, so the tests do not depend on today's date."""

    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10")

    def logs(self):
        return self.month(JAN).logs


class MatchTests(DatedCase):
    def test_saves_the_three_match_forms(self):
        self.do("7", "5 wraith", "4 2 octane")
        got = [(e.legend, e.kills, e.wins, e.src) for e in self.logs()]
        self.assertEqual(got, [("-", 7, 0, SRC_MATCH), ("Wraith", 5, 1, SRC_MATCH), ("Octane", 4, 2, SRC_MATCH)])

    def test_a_match_moves_the_account_totals_once_they_are_set(self):
        self.do("account 1000 100", "7 1 wraith")
        self.assertEqual((self.account().kills, self.account().wins), (1007, 101))

    def test_a_match_before_the_account_is_set_leaves_it_unset(self):
        self.do("7 1 wraith")
        self.assertIsNone(self.account())

    def test_negative_kills_are_rejected(self):
        self.assertIn("cannot be negative", self.do("-3 0"))
        self.assertFalse(self.has_month(JAN))

    def test_a_number_among_the_legend_tokens_is_an_error_in_every_format(self):
        for line in ("5 1 wraith 57", "5 wraith 57", "5 1 57", "5k wraith 57", "1w 57"):
            with self.subTest(line=line):
                self.assertIn("matches take no level", self.do(line))
                self.assertFalse(self.has_month(JAN))

    def test_anything_after_a_relative_level_is_an_error(self):
        self.assertIn("takes no legend", self.do("3l wraith"))
        self.assertFalse(self.has_month(JAN))

    def test_unrecognized_input_shows_the_menu(self):
        self.assertEqual(self.do("banana"), quick_guide())

    def test_there_is_no_m_command(self):
        self.do("7 1 wraith")
        self.assertEqual(self.do("m"), quick_guide())
        self.assertNotIn(" m ", help_text())


class AccountTests(DatedCase):
    def test_first_save_logs_nothing(self):
        self.do("account 1000 100")
        self.assertEqual(self.logs(), [])
        self.assertEqual(self.account().kills, 1000)

    def test_later_totals_log_the_gain(self):
        self.do("account 1000 100", "account 1010 101")
        entry = self.logs()[0]
        self.assertEqual((entry.legend, entry.kills, entry.wins, entry.src), ("-", 10, 1, SRC_ACCOUNT))
        self.assertEqual(self.account().kills, 1010)

    def test_undo_of_a_gain_restores_the_totals_exactly(self):
        self.do("account 1000 100", "account 1010 101", "undo")
        self.assertEqual(self.logs(), [])
        self.assertEqual((self.account().kills, self.account().wins), (1000, 100))

    def test_same_totals_log_nothing(self):
        self.assertIn("already up to date", self.do("account 1000 100", "account 1000 100"))
        self.assertEqual(self.logs(), [])

    def test_declined_lowering_changes_nothing(self):
        self.do("account 1000 100")
        self.answer = False
        self.assertIn(ABORTED, self.do("account 900 100"))
        self.assertEqual(self.account().kills, 1000)

    def test_confirmed_lowering_logs_nothing_and_undo_restores(self):
        self.do("account 1000 100", "account 900 100")
        self.assertEqual(self.asked, 1)
        self.assertEqual(self.account().kills, 900)
        self.assertEqual(self.logs(), [])
        self.do("undo")
        self.assertEqual(self.account().kills, 1000)


class BaseTests(DatedCase):
    def test_first_set_logs_nothing_and_keeps_the_account(self):
        self.do("account 1000 100", "base wraith 500 50")
        self.assertEqual(self.logs(), [])
        self.assertEqual(self.bases()["Wraith"].kills, 500)
        self.assertEqual(self.account().kills, 1000)

    def test_first_set_excludes_what_is_already_logged(self):
        self.do("7 1 wraith", "base wraith 500 50")
        self.assertEqual((self.bases()["Wraith"].kills, self.bases()["Wraith"].wins), (493, 49))

    def test_a_gain_is_logged_and_reaches_the_account(self):
        self.do("account 1000 100", "base wraith 500 50", "base wraith 510 52")
        entry = self.logs()[0]
        self.assertEqual((entry.legend, entry.kills, entry.wins, entry.src), ("Wraith", 10, 2, SRC_BASE))
        self.assertEqual(self.account().kills, 1010)

    def test_undo_of_a_gain_takes_it_back_out(self):
        self.do("account 1000 100", "base wraith 500 50", "base wraith 510 52", "undo")
        self.assertEqual(self.logs(), [])
        self.assertEqual(self.account().kills, 1000)
        self.assertEqual(self.bases()["Wraith"].kills, 500)

    def test_totals_below_the_logged_values_are_refused_without_asking(self):
        self.do("base wraith 500 50", "7 1 wraith")
        self.assertIn("can't be lower", self.do("base wraith 3 0"))
        self.assertEqual(self.asked, 0)
        self.assertEqual(self.bases()["Wraith"].kills, 500)

    def test_a_correction_asks_first_and_logs_nothing(self):
        self.do("base wraith 500 50", "base wraith 400 50")
        self.assertEqual(self.asked, 1)
        self.assertEqual(self.bases()["Wraith"].kills, 400)
        self.assertEqual(self.logs(), [])

    def test_undo_restores_a_corrected_base(self):
        self.do("base wraith 500 50", "base wraith 400 50", "undo")
        self.assertEqual(self.bases()["Wraith"].kills, 500)

    def test_zero_zero_removes_and_undo_restores(self):
        self.do("base wraith 500 50", "base wraith 0 0")
        self.assertNotIn("Wraith", self.bases())
        self.do("undo")
        self.assertEqual(self.bases()["Wraith"].kills, 500)

    def test_removing_a_legend_with_no_base_is_an_error(self):
        self.assertIn("no base to remove", self.do("base wraith 0 0"))


class LevelTests(DatedCase):
    def test_relative_level_needs_a_first_level(self):
        self.assertIn("no level recorded", self.do("3l"))

    def test_relative_level_adds_to_the_last_one(self):
        self.do("accountl 700", "3l")
        self.assertEqual(self.logs()[-1].level, 703)

    def test_declined_lower_level_is_not_saved(self):
        self.do("accountl 700")
        self.answer = False
        self.assertIn(ABORTED, self.do("accountl 600"))
        self.assertEqual([e.level for e in self.logs()], [700])

    def test_one_confirmation_covers_the_whole_account_command(self):
        self.do("account 1000 100 700", "account 900 100 600")
        self.assertEqual(self.asked, 1)


class StickyTests(DatedCase):
    def test_off_by_default(self):
        self.do("7")
        self.assertEqual(self.logs()[0].legend, "-")

    def test_pin_needs_a_base_legend(self):
        self.assertIn("Invalid or missing", self.do("p wraith"))
        self.assertIsNone(self.session.sticky.legend)

    def test_locked_legend_applies_to_matches_and_quick_entries(self):
        self.do("base wraith 5 5", "p wraith", "3 0", "5k", "1w")
        self.assertEqual([e.legend for e in self.logs()], ["Wraith"] * 3)

    def test_a_typed_legend_leaves_the_lock_alone(self):
        self.do("base wraith 5 5", "p wraith", "3 0 octane", "2k octane")
        self.assertEqual([e.legend for e in self.logs()], ["Octane", "Octane"])
        self.assertEqual(self.session.sticky.legend, "Wraith")

    def test_dash_unlocks_and_saves_nothing(self):
        self.do("base wraith 5 5", "p wraith", "-")
        self.assertIsNone(self.session.sticky.legend)
        self.assertEqual(self.logs(), [])

    def test_a_typed_dash_in_a_match_unlocks_and_saves_with_no_legend(self):
        self.do("base wraith 5 5", "p wraith", "5 1 -")
        self.assertIsNone(self.session.sticky.legend)
        self.assertEqual(self.logs()[0].legend, "-")

    def test_a_typed_dash_in_a_quick_entry_unlocks_and_saves_with_no_legend(self):
        for line in ("5k -", "1w -"):
            with self.subTest(line=line):
                self.do("base wraith 5 5", "p wraith", line)
                self.assertIsNone(self.session.sticky.legend)
                self.assertEqual(self.logs()[-1].legend, "-")

    def test_a_number_alone_counts_like_typing_the_locked_legend(self):
        self.do("base wraith 5 5", "4 wraith", "p wraith", "4")
        typed, pinned = self.logs()
        self.assertEqual((pinned.legend, pinned.kills, pinned.wins), (typed.legend, typed.kills, typed.wins))
        self.assertEqual(pinned.wins, 1)

    def test_two_numbers_keep_their_wins_with_a_locked_legend(self):
        self.do("base wraith 5 5", "p wraith", "4 0")
        self.assertEqual((self.logs()[0].kills, self.logs()[0].wins), (4, 0))

    def test_levels_never_take_the_locked_legend(self):
        self.do("base wraith 5 5", "p wraith", "accountl 700")
        self.assertEqual(self.logs()[0].legend, "-")


class LegendResolutionTests(DatedCase):
    def setUp(self):
        super().setUp()
        self.do("base wraith 5 5", "base bangalore 5 5", "base bloodhound 5 5")

    def legends(self):
        return [e.legend for e in self.logs()]

    def test_a_prefix_saves_the_known_legend_without_asking(self):
        self.do("7 1 wra", "7 WRA", "5k wra", "1w wra")
        self.assertEqual(self.legends(), ["Wraith"] * 4)
        self.assertEqual(self.new_legends, [])

    def test_exact_match_wins_over_a_longer_legend(self):
        self.do("base wraith x 5 5", "7 1 wraith")
        self.assertEqual(self.legends(), ["Wraith"])

    def test_several_matches_are_rejected_without_asking(self):
        out = self.do("7 1 b")
        self.assertIn("Bangalore, Bloodhound", out)
        self.assertEqual(self.legends(), [])
        self.assertEqual(self.new_legends, [])

    def test_unknown_legend_created_on_yes_and_known_afterwards(self):
        self.do("7 1 zzz", "3 0 zz")
        self.assertEqual(self.legends(), ["Zzz", "Zzz"])
        self.assertEqual(self.new_legends, ["Zzz"])

    def test_unknown_legend_aborted_on_no(self):
        self.create_legends = False
        for line in ("7 1 zzz", "5k zzz"):
            with self.subTest(line=line):
                self.assertIn(ABORTED, self.do(line))
        self.assertEqual(self.legends(), [])

    def test_no_legend_and_dash_never_ask(self):
        self.do("7", "7 1 -", "5k")
        self.assertEqual(self.new_legends, [])

    def test_the_locked_legend_never_asks(self):
        self.do("p wraith", "3 0", "2k")
        self.assertEqual(self.new_legends, [])

    def test_legends_of_earlier_months_are_known(self):
        self.do("7 1 zzz", "date 2025-02-01", "3 0 zz")
        self.assertEqual(self.new_legends, ["Zzz"])
        self.assertEqual(self.month("2025-02").logs[0].legend, "Zzz")

    def test_the_prompt_and_its_answers(self):
        with patch("builtins.input", return_value="y") as ask:
            self.assertTrue(confirm_new_legend("Zzz"))
        ask.assert_called_once_with("Unknown legend 'Zzz'. Create new? (y/n): ")
        with patch("builtins.input", return_value="n"):
            self.assertFalse(confirm_new_legend("Zzz"))
        with patch("builtins.input", side_effect=EOFError), patch("builtins.print"):
            self.assertFalse(confirm_new_legend("Zzz"))


class UndoTests(DatedCase):
    def test_nothing_recorded(self):
        self.assertEqual(self.do("undo"), "No data recorded yet.\n")

    def test_undo_is_last_in_first_out(self):
        self.do("7 1 wraith", "3 0 octane", "undo")
        self.assertEqual([e.legend for e in self.logs()], ["Wraith"])

    def test_shows_what_the_next_undo_would_revert(self):
        out = self.do("7 1 wraith", "3 0 octane", "undo")
        self.assertIn("PREVIOUS LOG: [MATCH]", out)
        self.assertIn("Legend: Wraith", out)

    def test_an_emptied_month_file_is_removed(self):
        self.do("7 1 wraith", "undo")
        self.assertFalse(self.has_month(JAN))


class DateTests(SessionCase):
    def test_a_future_date_is_refused_and_the_active_date_stays(self):
        self.do("date 2025-01-10")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        out = self.do(f"date {tomorrow}")
        self.assertIn("in the future", out)
        self.assertEqual(self.session.day, "2025-01-10")

    def test_today_and_past_days_are_accepted(self):
        self.do(f"date {date.today().isoformat()}")
        self.assertEqual(self.session.day, date.today().isoformat())
        self.do("date 2025-01-10")
        self.assertEqual(self.session.day, "2025-01-10")

    def test_date_today_clears_the_active_date(self):
        self.do("date 2025-01-10", "date today")
        self.assertIsNone(self.session.day)

    def test_a_malformed_date_shows_the_menu(self):
        self.assertEqual(self.do("date soon"), quick_guide())


class CombinedQuickTests(DatedCase):
    def last(self):
        e = self.logs()[-1]
        return e.legend, e.kills, e.wins, e.level, e.src

    def test_kills_wins_and_levels_with_a_legend(self):
        self.do("accountl 700", "5k 1w 2l wraith")
        self.assertEqual(self.last(), ("Wraith", 5, 1, 702, SRC_MATCH))

    def test_wins_can_be_omitted(self):
        self.do("accountl 700", "5k 2l wraith")
        self.assertEqual(self.last(), ("Wraith", 5, 0, 702, SRC_MATCH))

    def test_levels_can_be_omitted(self):
        self.do("accountl 700", "5k 1w wraith")
        self.assertEqual(self.last(), ("Wraith", 5, 1, 0, SRC_MATCH))

    def test_kills_can_be_omitted(self):
        self.do("accountl 700", "1w 2l wraith")
        self.assertEqual(self.last(), ("Wraith", 0, 1, 702, SRC_MATCH))

    def test_sticky_legend_with_every_combination(self):
        self.do("base wraith 5 5", "p wraith", "accountl 700")
        for line, want in (("5k 1w 2l", (5, 1, 702)), ("3k 1l", (3, 0, 703)), ("4k 1w", (4, 1, 0))):
            with self.subTest(line=line):
                self.do(line)
                self.assertEqual(self.last(), ("Wraith", *want, SRC_MATCH))

    def test_a_typed_legend_beats_the_lock_and_leaves_it_on(self):
        self.do("base wraith 5 5", "p wraith", "accountl 700", "5k 2l octane")
        self.assertEqual(self.last()[0], "Octane")
        self.assertEqual(self.session.sticky.legend, "Wraith")

    def test_a_typed_dash_unlocks(self):
        self.do("base wraith 5 5", "p wraith", "accountl 700", "5k 2l -")
        self.assertEqual(self.last()[0], "-")
        self.assertIsNone(self.session.sticky.legend)

    def test_without_a_level_nothing_is_saved_and_no_legend_is_asked(self):
        self.assertIn("no level recorded", self.do("5k 2l wraith"))
        self.assertFalse(self.has_month(JAN))
        self.assertEqual(self.new_legends, [])

    def test_a_declined_new_legend_saves_nothing(self):
        self.create_legends = False
        self.do("accountl 700")
        self.assertIn(ABORTED, self.do("5k 2l wraith"))
        self.assertEqual(len(self.logs()), 1)

    def test_the_saved_line_shows_the_new_level(self):
        self.assertIn("KILLS 5  WINS 1  LEVEL 702", self.do("accountl 700", "5k 1w 2l wraith"))

    def test_the_next_level_counts_from_it(self):
        self.do("accountl 700", "5k 2l wraith", "3l")
        self.assertEqual(self.last()[3], 705)

    def test_it_moves_the_account_totals(self):
        self.do("account 100 10 700", "5k 1w 2l wraith")
        self.assertEqual((self.account().kills, self.account().wins), (105, 11))

    def test_one_undo_reverts_the_whole_line(self):
        self.do("account 100 10 700", "5k 1w 2l wraith", "undo")
        self.assertEqual((self.account().kills, self.account().wins), (100, 10))
        self.assertEqual(self.do("3l").count("LEVEL 703"), 1)

    def test_previous_log_shows_its_level(self):
        out = self.do("accountl 700", "5k 2l wraith", "1k wraith", "undo")
        self.assertIn("[MATCH]", out)
        self.assertIn("LEVEL 702", out.split("PREVIOUS LOG:")[1])

    def test_it_shows_in_both_log_tables(self):
        self.do("accountl 700", "5k 2l wraith")
        out = self.do("log")
        self.assertIn("Wraith", out)
        self.assertIn("702", out)

    def test_a_lone_level_still_takes_no_legend(self):
        self.assertIn("takes no legend", self.do("accountl 700", "3l wraith"))


class LogTests(DatedCase):
    def rows(self):
        with patch("apex.display.colors.COLOR", True):
            return self.do("log").splitlines()

    def row(self, lines, legend):
        return next(line for line in lines if legend in line)

    def test_matches_show_win_as_w_green_and_loss_as_l_red(self):
        self.do("7 1 wraith", "3 0 octane", "4 2 bangalore")
        lines = self.rows()
        self.assertIn(green(f"{'W':<3}", True), self.row(lines, "Wraith"))
        self.assertIn(red(f"{'L':<3}", True), self.row(lines, "Octane"))
        self.assertIn(green(f"{'W':<3}", True), self.row(lines, "Bangalore"))

    def test_the_matches_table_header_is_win_like_g(self):
        self.do("7 1 wraith")
        self.assertRegex(self.do("log"), r"KILLS \| WIN\b")


class UnreadableFileTests(DatedCase):
    def test_reports_an_error_and_the_session_goes_on(self):
        self.do("7 1 wraith")
        path = self.month_file(JAN)
        os.remove(path)
        os.mkdir(path)  # open() raises OSError, as for a locked file
        out = self.do("k")
        self.assertTrue(out.startswith("Error: could not read the data files"), out)
        self.assertIn("APEX CAREER COUNT - HELP", self.do("help"))


if __name__ == "__main__":
    unittest.main()
