"""The single save path (save_log) and its wrappers, plus the LIFO undo."""
import os

from apex.config import ACC_TAG, DFMT, LEG_W, SRC_ACCOUNT, SRC_LEVEL, SRC_MATCH
from apex.core.aggregates import legend_totals, zero
from apex.core.levels import check_level, last_level, latest_level
from apex.core.parsing import LEVEL_RE, QUICK_RE, clean, parse_when
from apex.core.records import Change, Entry
from apex.display.messages import fmt_undo, logs_word
from apex.display.tables import summary
from apex.storage.account_file import bump_account, load_account, put_base, restore_account, save_account
from apex.storage.monthly_file import current_month, load, load_current, month_path, open_month, write_month


def save_log(d, kills, wins, legend=None, when=None, level=0, delta=None, account=None, source=SRC_MATCH):
    """Save one log entry (1 read + 1 atomic write). Errors -> ValueError.
    level = absolute level (0 = not recorded); delta (from "+<n>") = last level recorded
    before the entry's date + delta. Either way the level check runs. Only level updates
    (save_level) pass a level: matches never carry one.
    account = account totals already loaded by the caller (account_cmd), so they are not read twice.
    source = SRC code of the entry (match, account update, base update, level update).
    Returns (path, summary, current account level after the save, Entry)."""
    if kills < 0 or wins < 0 or level < 0:
        raise ValueError("Error: kills, wins and level cannot be negative.")
    if delta is not None and delta < 1:
        raise ValueError("Error: a +<n> level increment must be 1 or higher.")
    dt = parse_when(when)
    stamp = dt.strftime(DFMT)
    month, m = open_month(d, dt)  # a new month starts with the old totals and levels carried over
    if delta is not None:
        base = last_level(stamp, m.logs, m.lv)
        if not base:
            raise ValueError("Error: no level recorded yet; enter an absolute level first (e.g. 700).")
        level = base + delta
    check_level(level, stamp, m.logs, m.lv)

    acc = (account or load_account(d)) if (kills or wins) else None  # totals to bump (None = unset / nothing to add)
    rec = Entry(stamp, clean(legend, LEG_W), kills, wins, level, m.next_id(), 1 if acc else 0, source)
    m.logs.append(rec)
    m.logs.sort(key=lambda e: (e.date, e.id))
    if source == SRC_ACCOUNT and acc:  # snapshot of the totals before the gain, same ID: undo restores it exactly
        m.changes.append(Change(rec.id, stamp, ACC_TAG, tuple(acc)))
    path = write_month(d, month, m)
    if acc:  # keep the global account totals in step with the logs (after the monthly file)
        save_account(d, acc[0] + kills, acc[1] + wins)
    return path, summary(month, m.hist, m.prev, m.logs), latest_level(m.logs, m.lv), rec


def current_level(d):
    """Current account level from the current monthly file (one read); 0 if nothing recorded yet."""
    cur = current_month(d)
    if not cur:
        return 0
    m = load(month_path(d, cur))
    return latest_level(m.logs, m.lv)


def _rewrite(d, cur, path, m):
    """Write the month file back after an undo, or delete it once it holds nothing, so the
    previous month (left untouched at rollover) becomes current again. Returns the note."""
    if m.logs or m.changes:
        write_month(d, cur, m)
        return f"{logs_word(len(m.logs))} left in {cur}"
    os.remove(path)
    return f"{cur} is now empty, file removed; current month: {current_month(d) or 'none'}"


def undo(d):
    """Revert the most recent action (LIFO): every record of the file with the highest ID.
    That is one log entry, one Change (a base change or the first account save), or both: an
    account gain's entry and the snapshot of the totals before it, which share an ID.
    Each record is reverted on its own terms: a Change puts back the value it replaced; an entry
    takes its kills/wins back out of the account totals, unless a Change already restored them.
    The month file is written first, then account_stats.txt. Returns the text to print, which ends
    with the PREVIOUS LOG: the action that is now the most recent (the next undo would revert it)."""
    cur, path, m = load_current(d)
    entry, change = m.last_action()
    if not (entry or change):
        raise ValueError("Nothing to undo.")
    if entry:
        m.logs.remove(entry)
    if change:
        m.changes.remove(change)
    note = _rewrite(d, cur, path, m)
    if change and change.is_account:
        restore_account(d, change.old)
    elif change:
        put_base(d, change.target, change.old)
    if entry and entry.acc and not (change and change.is_account):
        bump_account(d, -entry.kills, -entry.wins)
    logged = None
    if change and not change.is_account:  # the legend's logged kills/wins, shown with its restored base
        t = legend_totals(m.hl, m.logs).get(change.target, zero())
        logged = (t[1], t[2])
    return fmt_undo(note, m.last_action(), entry, change, logged)


def save_level(d, token, when=None):
    """Level-only entry (wins/kills = 0): "700" = absolute level, "+5" = last level + 5.
    Always goes through save_log, so the level check runs."""
    if not LEVEL_RE.match(token):
        raise ValueError("Format: <n> (e.g. 700) or <n>l (e.g. 3l)")
    n = int(token)
    if n < 1:
        raise ValueError("Error: the level (or <n>l) must be 1 or higher.")
    if token.startswith("+"):
        return save_log(d, 0, 0, None, when, 0, delta=n, source=SRC_LEVEL)
    return save_log(d, 0, 0, None, when, n, source=SRC_LEVEL)


def save_quick(d, token, when=None, legend=None):
    """Single-token entries: "<n>" = absolute level, "<n>l" / "+<n>" = n more levels,
    "<n>k" = n kills only, "<n>w" = n wins only. Only quick kills/wins take legend (the REPL's
    pinned sticky legend); level updates never carry one."""
    m = QUICK_RE.match(token)
    if not m:
        return save_level(d, token, when)
    n, kind = int(m.group(1)), m.group(2).lower()
    if n < 1:
        raise ValueError("Error: <n>k, <n>w and <n>l need n of 1 or higher.")
    if kind == "l":
        return save_level(d, f"+{n}", when)
    return save_log(d, n, 0, legend, when) if kind == "k" else save_log(d, 0, n, legend, when)
