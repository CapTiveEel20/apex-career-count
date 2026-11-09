"""A base gain claims what an account gain of the same month already added, so nothing is counted twice:
the totals are the same whichever is typed first, a split gain is one action, and undo restores it exactly."""
import unittest

from apex.config import ACC_TAG, SRC_ACCOUNT, SRC_BASE, SRC_CLAIM
from apex.core.aggregates import unclaimed
from apex.core.records import Change, Entry, Stored, Tally
from tests.helpers import SessionCase
from tests.test_views import ALL, report_row

JAN, FEB = "2025-01", "2025-02"


def entry(eid, src, kills, wins):
    return Entry("2025-01-10 20:00", "-" if src == SRC_ACCOUNT else "Wraith", kills, wins, 0, eid, 1, src)


class UnclaimedTests(unittest.TestCase):
    def test_account_gains_minus_claims(self):
        logs = [entry(1, SRC_ACCOUNT, 100, 5), entry(2, SRC_CLAIM, 30, 1), entry(3, SRC_ACCOUNT, 20, 0)]
        self.assertEqual(unclaimed(logs, []), Tally(0, 90, 4))

    def test_kills_and_wins_apart_and_never_below_0(self):
        logs = [entry(1, SRC_ACCOUNT, 10, 0), entry(2, SRC_CLAIM, 50, 0), entry(3, SRC_ACCOUNT, 0, 3)]
        self.assertEqual(unclaimed(logs, []), Tally(0, 0, 3))

    def test_matches_and_unclaimed_base_gains_take_nothing(self):
        logs = [entry(1, SRC_ACCOUNT, 100, 5), entry(2, "M", 7, 1), entry(3, SRC_BASE, 40, 2)]
        self.assertEqual(unclaimed(logs, []), Tally(0, 100, 5))

    def test_an_account_change_that_is_not_a_gain_starts_over(self):
        logs = [entry(1, SRC_ACCOUNT, 100, 5), entry(3, SRC_ACCOUNT, 20, 1)]
        changes = [Change(1, "2025-01-10 20:00", ACC_TAG, Stored(900, 90, "")),  # gain 1's snapshot
                   Change(2, "2025-01-10 20:00", ACC_TAG, Stored(1000, 95, "")),  # a confirmed lowering
                   Change(3, "2025-01-10 20:00", ACC_TAG, Stored(990, 94, ""))]
        self.assertEqual(unclaimed(logs, changes), Tally(0, 20, 1))

    def test_a_base_change_does_not_start_over(self):
        logs = [entry(1, SRC_ACCOUNT, 100, 5)]
        self.assertEqual(unclaimed(logs, [Change(2, "2025-01-10 20:00", "Wraith", None)]), Tally(0, 100, 5))


class ClaimCase(SessionCase):
    START = ("date 2025-01-10", "account 1000 100", "base wraith 200 10", "base octane 50 5")

    def setUp(self):
        super().setUp()
        self.do(*self.START)

    def totals(self):
        """(account, report's logged kills and wins, {legend: all-time kills and wins in 'l'})."""
        acc = self.account()
        legends = {}
        for line in self.do("l").splitlines():
            cells = [c.strip() for c in line.split("|")]
            if cells[0] in ("Wraith", "Octane"):
                legends[cells[0]] = (cells[1], cells[2])
        return (acc.kills, acc.wins), report_row(self.do("report"), ALL)[:2], legends

    def logs(self):
        return [(e.src, e.legend, e.kills, e.wins) for e in self.month(JAN).logs]


class OrderTests(ClaimCase):
    SYNC = ("account 1100 105", "base wraith 300 15")
    EXPECTED = ((1100, 105), (100, 5), {"Wraith": ("300", "15"), "Octane": ("50", "5")})

    def test_account_first_counts_the_gain_once(self):
        self.do(*self.SYNC)
        self.assertEqual(self.totals(), self.EXPECTED)
        self.assertEqual(self.logs(), [(SRC_ACCOUNT, "-", 100, 5), (SRC_CLAIM, "Wraith", 100, 5)])

    def test_base_first_is_unchanged(self):
        self.do(*reversed(self.SYNC))
        self.assertEqual(self.totals(), self.EXPECTED)
        self.assertEqual(self.logs(), [(SRC_BASE, "Wraith", 100, 5)])

    def test_every_order_of_three_updates_gives_the_same_totals(self):
        lines = ("account 1130 107", "base wraith 300 15", "base octane 80 7")
        expected = ((1130, 107), (130, 7), {"Wraith": ("300", "15"), "Octane": ("80", "7")})
        orders = ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0))
        for order in orders:
            with self.subTest(order=order):
                self.setUp()
                self.do(*(lines[i] for i in order))
                self.assertEqual(self.totals(), expected)


class SplitTests(ClaimCase):
    def test_only_what_is_left_to_claim_is_claimed(self):
        self.do("account 1040 102", "base wraith 300 15")
        self.assertEqual(self.logs(), [(SRC_ACCOUNT, "-", 40, 2), (SRC_CLAIM, "Wraith", 40, 2), (SRC_BASE, "Wraith", 60, 3)])
        self.assertEqual(self.totals(), ((1100, 105), (100, 5), {"Wraith": ("300", "15"), "Octane": ("50", "5")}))

    def test_the_two_parts_are_one_action(self):
        self.do("account 1040 102", "base wraith 300 15")
        ids = [e.id for e in self.month(JAN).logs if e.legend == "Wraith"]
        self.assertEqual(len(set(ids)), 1)

    def test_it_says_what_was_already_counted(self):
        out = self.do("account 1040 102", "base wraith 300 15")
        self.assertIn("KILLS 40 | WINS 2 of it already counted by an account update", out)
        self.assertIn("SAVED  Wraith  KILLS 100  WINS 5", out)

    def test_kills_and_wins_are_claimed_apart(self):
        self.do("account 1100 100", "base wraith 300 15")
        self.assertEqual(self.logs(), [(SRC_ACCOUNT, "-", 100, 0), (SRC_CLAIM, "Wraith", 100, 0), (SRC_BASE, "Wraith", 0, 5)])
        self.assertEqual(self.totals()[0], (1100, 105))

    def test_a_pool_is_shared_by_the_legends_until_it_is_used_up(self):
        self.do("account 1100 105", "base wraith 270 13", "base octane 90 8")
        self.assertEqual(self.logs(), [(SRC_ACCOUNT, "-", 100, 5), (SRC_CLAIM, "Wraith", 70, 3),
                                       (SRC_CLAIM, "Octane", 30, 2), (SRC_BASE, "Octane", 10, 1)])
        self.assertEqual(self.totals(), ((1110, 106), (110, 6), {"Wraith": ("270", "13"), "Octane": ("90", "8")}))

    def test_a_claimed_gain_is_never_a_match(self):
        self.do("account 1100 105", "base wraith 300 15")
        self.assertIn("(no matches with kills this month)", self.do("g"))
        self.assertIn("(no matches logged this month)", self.do("log"))
        self.assertEqual(self.month(JAN).ll, {})

    def test_it_counts_for_its_legend_in_the_month(self):
        self.do("account 1100 105", "base wraith 300 15", "date 2025-02-01", "3 0 octane")
        feb = self.month(FEB)
        self.assertEqual(feb.hl["Wraith"], Tally(1, 100, 5))
        self.assertEqual(feb.hist, Tally(1, 100, 5))

    def test_nothing_is_claimed_across_months(self):
        self.do("account 1100 105", "date 2025-02-01", "base wraith 300 15")
        self.assertEqual(self.account().kills, 1200)

    def test_a_confirmed_lowering_of_the_account_leaves_nothing_to_claim(self):
        self.do("account 1100 105", "account 1050 103", "base wraith 300 15")
        self.assertEqual(self.account().kills, 1150)


class UndoTests(ClaimCase):
    def state(self):
        acc = self.account()
        return (acc.kills, acc.wins), {k: (v.kills, v.wins) for k, v in self.bases().items()}, self.month(JAN)

    def test_one_undo_reverts_a_split_gain_exactly(self):
        self.do("account 1040 102")
        before = self.state()
        self.do("base wraith 300 15", "undo")
        self.assertEqual(self.state(), before)

    def test_one_undo_reverts_a_whole_claim_exactly(self):
        self.do("account 1100 105")
        before = self.state()
        self.do("base wraith 300 15", "undo")
        self.assertEqual(self.state(), before)

    def test_undo_frees_what_was_claimed(self):
        self.do("account 1040 102", "base wraith 300 15")
        after = self.logs()
        self.do("undo", "base wraith 300 15")
        self.assertEqual(self.logs(), after)

    def test_undo_says_it_reverted_the_whole_gain(self):
        out = self.do("account 1040 102", "base wraith 300 15", "undo")
        self.assertIn("Wraith | WINS 5 | KILLS 100", out)
        self.assertIn("PREVIOUS LOG: [ACCOUNT UPDATE]", out)

    def test_previous_log_shows_the_whole_split_gain(self):
        out = self.do("account 1040 102", "base wraith 300 15", "7 1 octane", "undo")
        self.assertIn("PREVIOUS LOG: [BASE UPDATE]", out)
        self.assertIn("Legend: Wraith | KILLS +100 | WINS +5", out)

    def test_undoing_everything_goes_back_to_the_start_in_both_orders(self):
        for sync in (("account 1040 102", "base wraith 300 15"), ("base wraith 300 15", "account 1040 102")):
            with self.subTest(sync=sync):
                self.setUp()
                before = self.state()
                self.do(*sync, "undo", "undo")
                self.assertEqual(self.state(), before)


if __name__ == "__main__":
    unittest.main()
