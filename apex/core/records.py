"""Record types of the data files (no I/O): tallies and saved totals, log entries, undo records and a whole month."""
from typing import NamedTuple, Optional

from apex.config import ACC_TAG, SRC_LEVEL


class Tally(NamedTuple):
    """Totals of a set of log entries, in file-column order. logs = how many entries (stored, never shown)."""
    logs: int = 0
    kills: int = 0
    wins: int = 0

    def __add__(self, other):
        return Tally(self.logs + other.logs, self.kills + other.kills, self.wins + other.wins)


class Stored(NamedTuple):
    """Saved all-time totals: the global account totals or a legend's base."""
    kills: int
    wins: int
    updated: str

    @property
    def tally(self):
        return Tally(kills=self.kills, wins=self.wins)


class TopMatch(NamedTuple):
    """One row of the all-time highest-kill matches."""
    date: str
    legend: str
    kills: int
    wins: int


class LevelDay(NamedTuple):
    """A recorded account level; day = YYYY-MM-DD, or a full date and time for a current-month entry."""
    day: str
    level: int


class Periods(NamedTuple):
    """One Tally per reporting period."""
    month: Tally
    semi: Tally
    year: Tally
    alltime: Tally


class LegendRow(NamedTuple):
    """A legend and its Periods."""
    legend: str
    periods: Periods


class MatchTotals(NamedTuple):
    """All-time totals after a saved match: legend = None when it has none (legend_totals is then None
    too); account = the Stored account totals, None if never set."""
    legend: Optional[str]
    legend_totals: Optional[Tally]
    account: Optional[Stored]


class Quick(NamedTuple):
    """A parsed quick entry: kills, wins and levels to add (0 = omitted); legend = None if none typed."""
    kills: int
    wins: int
    levels: int
    legend: Optional[str]


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
    account totals; old = the Stored value it replaced, or None if there was none.
    An account gain's Change shares the ID of its Entry, so undo reverts both together."""
    id: int
    date: str
    target: str
    old: Optional[Stored]

    @property
    def is_account(self):
        return self.target == ACC_TAG


class Month(NamedTuple):
    """Everything one monthly file holds: the totals carried from earlier months (hist, prev, hl,
    pl, lv, ll), its log entries and its undo records (changes). The lists are updated in place.
    ll = {legend: date and time of its last match} in earlier months; top = the all-time highest-kill
    matches of earlier months, [TopMatch], best first; bests = the all-time monthly bests (each closed
    month's #1 match), [TopMatch], best first; damaged = lines of the file that could not be read,
    kept as they were."""
    hist: Tally
    prev: list
    logs: list
    hl: dict
    pl: list
    lv: list
    changes: list
    ll: dict
    top: list
    bests: list
    damaged: list

    @classmethod
    def empty(cls):
        return cls(Tally(), [], [], {}, [], [], [], {}, [], [], [])

    @property
    def has_records(self):
        """False once undo has taken everything out: its file can then be deleted."""
        return bool(self.logs or self.changes or self.damaged)

    def next_id(self):
        """Undo-stack ID for a new record: one above every log entry and change of the file."""
        return max([e.id for e in self.logs] + [c.id for c in self.changes], default=0) + 1

    def last_action(self):
        """(Entry, Change) of the most recent action, the records with the highest ID (what undo
        reverts next): one of them, both (an account gain and its snapshot), or (None, None)."""
        top = max([e.id for e in self.logs] + [c.id for c in self.changes], default=None)
        return (next((e for e in self.logs if e.id == top), None),
                next((c for c in self.changes if c.id == top), None))
