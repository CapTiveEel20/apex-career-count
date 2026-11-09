"""Random command sequences (fixed seeds, dates in 2025): undo restores every earlier state, and every
monthly file reads back exactly as it was written."""
import os
import random
import unittest
from unittest.mock import patch

from apex.config import ACC_TAG, FRE
from apex.core.records import Change, Entry, LevelDay, Month, Stored, Tally, TopMatch
from apex.storage.account_file import load_acct
from apex.storage.monthly_file import load, parse, render
from tests.helpers import SessionCase

SEEDS = 10
STEPS = 40
LEGENDS = ("wraith", "bangalore", "mad maggie", "octane", "wra", "-")
DAYS = ("2025-01-15", "2025-01-20", "2025-02-03", "2025-02-27", "2025-03-10", "2025-05-02", "2025-07-07", "2025-09-30")
EMPTY = (None, {}, {})


def random_command(r, state):
    """One line of input. Some are refused (a closed month, a lower total than logged): that is part of the test."""
    x, kills, wins, legend = r.random(), r.randint(0, 25), r.randint(0, 2), r.choice(LEGENDS)
    acc = state[0] or (100, 10)
    base = state[1].get("Wraith", (50, 5))
    if x < .25:
        return f"{kills} {wins} {legend}"
    if x < .32:
        return f"{kills}"
    if x < .42:
        return f"{max(kills, 1)}k {r.choice(['', '1w ', '1w 2l ', '2l '])}{legend}"
    if x < .50:
        return f"{r.randint(1, 5)}l"
    if x < .58:
        return f"accountl {r.randint(1, 2000)}"
    if x < .70:
        level = r.choice(["", f" {r.randint(1, 2000)}"])
        return f"account {acc[0] + r.randint(-5, 30)} {acc[1] + r.randint(-1, 3)}{level}"
    if x < .82:
        return "base wraith 0 0" if r.random() < .1 else f"base wraith {base[0] + r.randint(-5, 40)} {base[1] + r.randint(-1, 3)}"
    if x < .90:
        return f"date {r.choice(DAYS)}"
    return r.choice(("p wraith", "-"))


class MonthFormatTests(unittest.TestCase):
    def test_every_field_of_a_month_survives_render_and_parse(self):
        best = TopMatch("2025-01-10 21:00", "Octane", 12, 0)
        month = Month(
            hist=Tally(2, 19, 1),
            prev=[("2025-01", Tally(2, 19, 1))],
            logs=[Entry("2025-02-03 10:00", "Wraith", 7, 1, 700, 1, 1, "M"), Entry("2025-02-03 10:05", "-", 0, 0, 701, 2, 0, "L")],
            hl={"Octane": Tally(1, 12, 0), "Wraith": Tally(1, 7, 1)},
            pl=[("2025-01", "Octane", Tally(1, 12, 0))],
            lv=[LevelDay("2025-01-10", 699)],
            changes=[Change(3, "2025-02-03 10:06", "Wraith", Stored(50, 5, "2025-02-01 09:00")),
                     Change(4, "2025-02-03 10:07", ACC_TAG, None)],
            ll={"Wraith": "2025-01-10 21:00"},
            top=[best],
            bests=[best],
            damaged=["L | broken | line"],
        )
        for name, value in zip(month._fields, month):  # a new Month field must be filled in here too
            self.assertTrue(value, f"give Month.{name} a value in this test")
        self.assertEqual(parse(render("2025-02", month)), month)


class UndoInvariantTests(SessionCase):
    def months(self):
        return {FRE.match(n).group(1): load(os.path.join(self.d, n)) for n in os.listdir(self.d) if FRE.match(n)}

    def state(self):
        """(account kills/wins or None, {legend: base kills/wins}, {month: Month}): 'updated' stamps are not compared."""
        data = load_acct(self.d)
        acc = (data.account.kills, data.account.wins) if data.account else None
        return acc, {leg: (b.kills, b.wins) for leg, b in data.bases.items()}, self.months()

    @staticmethod
    def actions(state):
        """How many undoable actions a state holds: one per distinct ID."""
        return sum(len({e.id for e in m.logs} | {c.id for c in m.changes}) for m in state[2].values())

    def assert_round_trip(self, line):
        for month, m in self.months().items():
            self.assertEqual(parse(render(month, m)), m, f"{month} after {line!r}")

    def unwind(self, stack):
        """Undo the newest command (one that saved a level and totals is two actions); the state must be the one before it."""
        before, count, line = stack.pop()
        for _ in range(count):
            self.do("undo")
        self.assertEqual(self.state(), before, f"undo of {line!r}")

    def run_seed(self, seed):
        r = random.Random(seed)
        self.do("date today", "-", "date 2025-01-10")
        stack = []
        for _ in range(STEPS):
            before = self.state()
            line = random_command(r, before)
            self.do(line)
            self.assert_round_trip(line)
            after = self.state()
            count = self.actions(after) - self.actions(before)
            if count:
                stack.append((before, count, line))
            else:
                self.assertEqual(after, before, f"{line!r} changed the data without an undoable action")
            if stack and r.random() < .1:
                self.unwind(stack)
        while stack:
            self.unwind(stack)
        self.assertEqual(self.state(), EMPTY, f"seed {seed}")

    def test_undo_restores_every_state_and_files_read_back_the_same(self):
        with patch("apex.storage.atomic.os.fsync"):  # thousands of saves: no need to reach the disk
            for seed in range(SEEDS):
                self.run_seed(seed)
