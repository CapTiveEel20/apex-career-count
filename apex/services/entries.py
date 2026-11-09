"""The two save paths (record_gain: kills/wins; record_level: account level), the single-entry
commands built on them (save_match, save_quick) and the LIFO undo."""
from typing import NamedTuple, Optional

from apex.config import ABORTED, LEG_W, NO_LEGEND, SRC_LEVEL, SRC_MATCH
from apex.core.aggregates import legend_totals
from apex.core.levels import check_later, last_level
from apex.core.parsing import clean, resolve_legend
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


def record_gain(ledger, kills, wins, legend=None, source=SRC_MATCH, level=0):
    """Add one entry of kills/wins to the ledger and return it. source = where it came from:
    a match, an account gain or a base gain. level = the absolute account level reached with it
    (0 = none), so one undo reverts both."""
    if kills < 0 or wins < 0:
        raise ValueError("Error: kills, wins and level cannot be negative.")
    stamp = ledger.stamp
    m = ledger.open_month()  # a new month starts with the old totals and levels carried over
    if level:
        check_later(level, stamp, m.logs)
    acc = 1 if (kills or wins) and ledger.account else 0  # 1 = its kills/wins move the account totals
    rec = Entry(stamp, clean(legend, LEG_W), kills, wins, level, m.next_id(), acc, source)
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


def _match_legend(ledger, legend, confirm_legend):
    """The legend a match is saved under: a known one (a base or any logged legend) by exact name or
    prefix; a name nobody knows only if confirm_legend(name) agrees, else ValueError(ABORTED)."""
    name = clean(legend, LEG_W)
    if name == NO_LEGEND:
        return name
    m = ledger.current
    known = resolve_legend(name, set(ledger.bases) | set(legend_totals(m.hl, m.logs)))
    if known:
        return known
    if not confirm_legend(name):
        raise ValueError(ABORTED)
    return name


def save_match(d, kills, wins, legend, when, confirm_legend):
    """Save one match on its own. confirm_legend(name) = may this unknown legend be created? Returns Saved."""
    with Ledger(d, when) as ledger:
        rec = record_gain(ledger, kills, wins, _match_legend(ledger, legend, confirm_legend))
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


def _raised_level(ledger, n):
    """The account level n above the last one recorded; ValueError if there is none yet."""
    m = ledger.open_month()
    last = last_level(ledger.stamp, m.logs, m.lv)
    if not last:
        raise ValueError("Error: no level recorded yet; set it first with accountl <n> (e.g. accountl 700).")
    return last + n


def save_quick(d, quick, when, legend, confirm_legend):
    """A quick entry (Quick, from parse_quick). Kills and/or wins, with any levels, are one entry under
    legend (typed, or the REPL's pinned sticky legend; see save_match for confirm_legend). Levels
    alone are a level update and never carry a legend. Returns Saved."""
    with Ledger(d, when) as ledger:
        level = _raised_level(ledger, quick.levels) if quick.levels else 0  # before asking about a new legend
        if not (quick.kills or quick.wins):
            return _saved(ledger, record_level(ledger, level))
        rec = record_gain(ledger, quick.kills, quick.wins, _match_legend(ledger, legend, confirm_legend), level=level)
        return _saved(ledger, rec, _match_totals(ledger, rec))
