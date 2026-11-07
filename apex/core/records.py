"""Record types of a monthly data file (no I/O): log entries, undo records and a whole month."""
from typing import NamedTuple, Optional

from apex.config import ACC_TAG, SRC_LEVEL
from apex.core.aggregates import zero


class Entry(NamedTuple):
    """One log entry (an L line). acc = 1 if its kills/wins were added to the account totals;
    src = where it came from: SRC_MATCH, SRC_ACCOUNT, SRC_BASE or SRC_LEVEL."""
    date: str
    legend: str
    kills: int
    wins: int
    level: int
    id: int
    acc: int
    src: str

    @property
    def level_only(self):
        return self.src == SRC_LEVEL


class Change(NamedTuple):
    """Undo record (an @BU line): target = the legend whose base changed, or ACC_TAG for the global
    account totals; old = the value it replaced, (kills, wins, updated), or None if there was none.
    An account gain's Change shares the ID of its Entry, so undo reverts both together."""
    id: int
    date: str
    target: str
    old: Optional[tuple]

    @property
    def is_account(self):
        return self.target == ACC_TAG


class Month(NamedTuple):
    """Everything one monthly file holds: the totals carried from earlier months (hist, prev, hl,
    pl, lv, ll), its log entries and its undo records (changes). The lists are updated in place.
    ll = {legend: date and time of its last match} in earlier months; top = the all-time highest-kill
    matches of earlier months, [(date, legend, kills, wins)], best first."""
    hist: list
    prev: list
    logs: list
    hl: dict
    pl: list
    lv: list
    changes: list
    ll: dict
    top: list

    @classmethod
    def empty(cls):
        return cls(zero(), [], [], {}, [], [], [], {}, [])

    def next_id(self):
        """Undo-stack ID for a new record: one above every log entry and change of the file."""
        return max([e.id for e in self.logs] + [c.id for c in self.changes], default=0) + 1

    def last_action(self):
        """(Entry, Change) of the most recent action, the records with the highest ID (what undo
        reverts next): one of them, both (an account gain and its snapshot), or (None, None)."""
        top = max([e.id for e in self.logs] + [c.id for c in self.changes], default=None)
        return (next((e for e in self.logs if e.id == top), None),
                next((c for c in self.changes if c.id == top), None))
