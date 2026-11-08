"""The two save paths (record_gain: kills/wins; record_level: account level), the single-entry
commands built on them (save_match, save_quick) and the LIFO undo."""
from typing import NamedTuple, Optional

from apex.config import LEG_W, NO_LEGEND, SRC_LEVEL, SRC_MATCH
from apex.core.aggregates import legend_totals
from apex.core.levels import check_later, last_level
from apex.core.parsing import QUICK_RE, clean
from apex.core.records import Entry, MatchTotals, Stored, Tally
from apex.display.messages import fmt_undo, logs_word
from apex.storage.ledger import Ledger
from apex.storage.monthly_file import current_month


class Saved(NamedTuple):
    """A saved match or quick entry: its Entry, the current account level and the all-time totals
    (see _match_totals; None for a level update)."""
    entry: Entry
    level: int
    totals: Optional[MatchTotals]


def _saved(ledger, entry, totals=None):
    return Saved(entry, ledger.level(), totals)


def _match_totals(ledger, rec):
    """All-time totals after a saved match, for fmt_totals. Legend totals = base + logged."""
    if rec.legend == NO_LEGEND:
        return MatchTotals(None, None, ledger.account)
    m = ledger.current
    logged = legend_totals(m.hl, m.logs).get(rec.legend, Tally())
    return MatchTotals(rec.legend, logged + ledger.bases.get(rec.legend, Stored(0, 0, "")).tally, ledger.account)


def record_gain(ledger, kills, wins, legend=None, source=SRC_MATCH):
    """Add one entry of kills/wins to the ledger and return it. source = where it came from:
    a match, an account gain or a base gain."""
    if kills < 0 or wins < 0:
        raise ValueError("Error: kills, wins and level cannot be negative.")
    stamp = ledger.stamp
    m = ledger.open_month()  # a new month starts with the old totals and levels carried over
    acc = 1 if (kills or wins) and ledger.account else 0  # 1 = its kills/wins move the account totals
    rec = Entry(stamp, clean(legend, LEG_W), kills, wins, 0, m.next_id(), acc, source)
    ledger.add(rec)
    return rec


def record_level(ledger, level):
    """Add one level update (the absolute level, 1 or higher) to the ledger and return it.
    The caller has already had any lowering confirmed."""
    stamp = ledger.stamp
    m = ledger.open_month()
    check_later(level, stamp, m.logs)
    rec = Entry(stamp, NO_LEGEND, 0, 0, level, m.next_id(), 0, SRC_LEVEL)
    ledger.add(rec)
    return rec


def save_match(d, kills, wins, legend=None, when=None):
    """Save one match on its own. Returns Saved."""
    with Ledger(d, when) as ledger:
        rec = record_gain(ledger, kills, wins, legend)
        return _saved(ledger, rec, _match_totals(ledger, rec))


def undo(d):
    """Revert the most recent action (LIFO): one log entry, one Change (a base change, the first
    account save or a confirmed lowering of the account totals), or both: an account gain's entry
    and the snapshot of the totals before it, which share an ID (see Ledger.revert_last).
    Returns the text to print, which ends with the PREVIOUS LOG: the action that is now the most
    recent (the next undo would revert it)."""
    with Ledger(d) as ledger:
        entry, change = ledger.revert_last()
    cur, m = ledger.month, ledger.current
    if m.has_records:
        note = f"{logs_word(len(m.logs))} left in {cur}"
    else:
        note = f"{cur} is now empty, file removed; current month: {current_month(d) or 'none'}"
    logged = None
    if change and not change.is_account:  # the legend's logged kills/wins, shown with its restored base
        logged = legend_totals(m.hl, m.logs).get(change.target, Tally())
    return fmt_undo(note, m.last_action(), entry, change, logged)


def save_quick(d, token, when=None, legend=None):
    """Quick entries (token already checked by parse_quick): "<n>l" = n more levels, "<n>k" = n kills
    only, "<n>w" = n wins only. Only quick kills/wins take legend (the REPL's pinned sticky legend);
    level updates never carry one. Returns Saved."""
    match = QUICK_RE.match(token)
    n, kind = int(match.group(1)), match.group(2).lower()
    if n < 1:
        raise ValueError("Error: <n>k, <n>w and <n>l need n of 1 or higher.")
    if kind == "k":
        return save_match(d, n, 0, legend, when)
    if kind == "w":
        return save_match(d, 0, n, legend, when)
    with Ledger(d, when) as ledger:
        m = ledger.open_month()
        last = last_level(ledger.stamp, m.logs, m.lv)
        if not last:
            raise ValueError("Error: no level recorded yet; set it first with accountl <n> (e.g. accountl 700).")
        return _saved(ledger, record_level(ledger, last + n))
