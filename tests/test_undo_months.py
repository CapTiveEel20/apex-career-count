"""Undo of a month's first record: what it shows next, and that the totals its file carries are never lost."""
import os

from apex.core.records import Tally
from tests.helpers import SessionCase

JAN, FEB, MAR = "2025-01", "2025-02", "2025-03"


class PreviousLogTests(SessionCase):
    def test_shows_the_last_action_of_the_month_before(self):
        self.do("date 2025-01-10", "7 1 wraith", "date 2025-02-10", "3 0 octane")
        out = self.do("undo")
        self.assertIn(f"current month: {JAN}", out)
        self.assertIn("PREVIOUS LOG: [MATCH]", out)
        self.assertIn("Legend: Wraith", out)

    def test_it_is_what_the_next_undo_reverts(self):
        self.do("date 2025-01-10", "7 1 wraith", "date 2025-02-10", "3 0 octane", "undo")
        self.assertIn("Wraith", self.do("undo").split("PREVIOUS LOG")[0])

    def test_labels_a_base_change_of_the_month_before(self):
        self.do("date 2025-01-10", "base wraith 10 1", "date 2025-02-10", "3 0 octane")
        out = self.do("undo")
        self.assertIn("PREVIOUS LOG: [BASE UPDATE]", out)
        self.assertIn("Legend: Wraith", out)

    def test_inside_a_month_it_is_the_action_before(self):
        self.do("date 2025-01-10", "7 1 wraith", "3 0 octane")
        out = self.do("undo")
        self.assertIn("1 log left", out)
        self.assertIn("PREVIOUS LOG: [MATCH]", out)

    def test_is_none_when_nothing_is_left(self):
        self.do("date 2025-01-10", "7 1 wraith")
        out = self.do("undo")
        self.assertIn("current month: none", out)
        self.assertIn("PREVIOUS LOG: none", out)
        self.assertFalse(self.has_month(JAN))


class CarriedTotalsTests(SessionCase):
    CARRIED = Tally(2, 19, 1)

    def setUp(self):
        super().setUp()
        self.do("date 2025-01-10", "7 1 wraith", "12 0 octane", "date 2025-02-10", "3 0 wraith")

    def drop(self, month):
        os.remove(self.month_file(month))

    def test_the_file_is_removed_when_the_month_before_is_there(self):
        self.do("undo")
        self.assertFalse(self.has_month(FEB))
        self.assertTrue(self.has_month(JAN))

    def test_the_file_is_kept_when_the_month_before_is_gone(self):
        self.drop(JAN)
        out = self.do("undo")
        self.assertTrue(self.has_month(FEB))
        self.assertIn("file kept", out)
        self.assertNotIn("file removed", out)
        self.assertIn("PREVIOUS LOG: none", out)

    def test_a_kept_file_holds_everything_it_carried_and_no_records(self):
        self.drop(JAN)
        self.do("undo")
        feb = self.month(FEB)
        self.assertEqual(feb.hist, self.CARRIED)
        self.assertEqual(feb.hl["Octane"], Tally(1, 12, 0))
        self.assertEqual([r.kills for r in feb.top], [12, 7])
        self.assertEqual([r.kills for r in feb.bests], [12])
        self.assertEqual((feb.logs, feb.changes), ([], []))

    def test_there_is_nothing_more_to_undo_after_it(self):
        self.drop(JAN)
        self.assertIn("Nothing to undo", self.do("undo", "undo"))
        self.assertTrue(self.has_month(FEB))

    def test_a_kept_file_takes_new_records(self):
        self.drop(JAN)
        self.do("undo", "4 0 wraith")
        feb = self.month(FEB)
        self.assertEqual(feb.hist, self.CARRIED)
        self.assertEqual([e.kills for e in feb.logs], [4])

    def test_a_kept_file_rolls_over(self):
        self.drop(JAN)
        self.do("undo", "date 2025-03-01", "1 0 wraith")
        self.assertEqual(self.month(MAR).hist, self.CARRIED)
        self.assertEqual([r.kills for r in self.month(MAR).top], [12, 7])

    def test_the_file_is_kept_when_a_month_in_between_is_gone(self):
        self.do("date 2025-03-05", "1 0 wraith")
        self.drop(FEB)
        self.do("undo")
        self.assertTrue(self.has_month(MAR))
        self.assertEqual(self.month(MAR).hist, Tally(3, 22, 1))


class NothingCarriedTests(SessionCase):
    def test_a_month_after_one_with_no_entries_is_removed(self):
        self.do("date 2025-01-10", "base wraith 10 1", "date 2025-02-10", "3 0 wraith", "undo")
        self.assertFalse(self.has_month(FEB))
        self.assertTrue(self.has_month(JAN))

    def test_a_month_after_a_gap_in_the_calendar_is_removed(self):
        self.do("date 2025-01-10", "7 1 wraith", "date 2025-04-10", "3 0 wraith", "undo")
        self.assertFalse(self.has_month("2025-04"))
        self.assertTrue(self.has_month(JAN))
