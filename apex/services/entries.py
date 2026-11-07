"""The single save path (save_log) and its wrappers, plus the LIFO undo."""
import os

from apex.config import ACC_TAG, DFMT, LEG_W, SRC_ACCOUNT, SRC_LEVEL, SRC_MATCH
from apex.core.aggregates import legend_totals, zero
from apex.core.levels import check_level, last_level, latest_level
from apex.core.parsing import LEVEL_RE, QUICK_RE, clean, parse_when
from apex.display.colors import orange, paint
from apex.display.messages import logs_word
from apex.display.tables import summary
from apex.storage.account_file import bump_account, load_account, restore_account, restore_base, save_account
from apex.storage.atomic import write_atomic
from apex.storage.monthly_file import (current_month, current_path, load, month_path, next_id,
                                       read_month, render, roll_over)


def save_log(d, kills, wins, legend=None, when=None, level=0, delta=None, account=None, source=SRC_MATCH):
    """Save one log entry (1 read + 1 atomic write). Errors -> ValueError.
    level = absolute level (0 = not recorded); delta (from "+<n>") = last level recorded
    before the entry's date + delta. Either way the level check runs. Only level updates
    (save_level) pass a level: matches never carry one.
    account = account totals already loaded by the caller (account_cmd), so they are not read twice.
    source = SRC code of the entry (match, account update, base update, level update).
    Returns (path, summary, current account level after the save, record)."""
    if kills < 0 or wins < 0 or level < 0:
        raise ValueError("Error: kills, wins and level cannot be negative.")
    if delta is not None and delta < 1:
        raise ValueError("Error: a +<n> level increment must be 1 or higher.")
    dt = parse_when(when)
    stamp = dt.strftime(DFMT)

    cur, month, state = read_month(d, dt.strftime("%Y-%m"))
    _, _, logs, _, _, lv, _ = state
    if delta is not None:
        base = last_level(stamp, logs, lv)
        if not base:
            raise ValueError("Error: no level recorded yet; enter an absolute level first (e.g. 700).")
        level = base + delta
    check_level(level, stamp, logs, lv)

    if cur and month > cur:  # new month -> new file, totals carried into the header
        state = roll_over(cur, month, dt.date(), state)
    hist, prev, logs, hl, pl, lv, bu = state

    acc = (account or load_account(d)) if (kills or wins) else None  # totals to bump (None = unset / nothing to add)
    rec = (stamp, clean(legend, LEG_W), kills, wins, level, next_id(logs, bu), 1 if acc else 0, source)
    logs.append(rec)
    logs.sort(key=lambda r: (r[0], r[5]))
    if source == SRC_ACCOUNT and acc:  # snapshot of the totals before the gain, same ID: undo restores it exactly
        bu.append((rec[5], stamp, ACC_TAG, tuple(acc)))
    path = month_path(d, month)
    write_atomic(path, render(month, hist, prev, logs, hl, pl, lv, bu))
    if acc:  # keep the global account totals in step with the logs (after the monthly file)
        save_account(d, acc[0] + kills, acc[1] + wins)
    return path, summary(month, hist, prev, logs), latest_level(logs, lv), rec


def current_level(d):
    """Current account level from the current monthly file (one read); 0 if nothing recorded yet."""
    cur = current_month(d)
    if not cur:
        return 0
    _, _, logs, _, _, lv, _ = load(month_path(d, cur))
    return latest_level(logs, lv)


def _rewrite(d, cur, path, state):
    """Write the month file back after an undo, or delete it once it holds nothing, so the
    previous month (left untouched at rollover) becomes current again. Returns the note."""
    hist, prev, logs, hl, pl, lv, bu = state
    if logs or bu:
        write_atomic(path, render(cur, hist, prev, logs, hl, pl, lv, bu))
        return f"{logs_word(len(logs))} left in {cur}"
    os.remove(path)
    return f"{cur} is now empty, file removed; current month: {current_month(d) or 'none'}"


def _entry_line(r):
    """One log entry as shown by undo: date | legend | wins | kills | level."""
    return (f"{r[0]} | {r[1]} | " + paint(f"WINS {r[3]:,} | KILLS {r[2]:,}") +
            " | " + orange(f"LEVEL {r[4]:,}"))


def _latest_line(logs):
    """After an undo: the new most recent log entry (highest ID left), the one the next undo takes."""
    last = max(logs, key=lambda r: r[5], default=None)
    return "Latest entry now: " + (_entry_line(last) if last else "none (no entries left in this file)") + "\n"


def undo(d):
    """Remove the most recent record (LIFO by ID): a log entry, a base change (@BU), whose
    previous base is put back, or a first-time account save (@BU with legend @ACCOUNT), whose
    previous totals (none) are put back. An account gain entry (SRC A) has an @BU snapshot with
    its own ID: both go together and the totals before the gain are restored exactly.
    The month file is written first, then account_stats.txt.
    The reply ends with the new latest log entry, so the current state is visible."""
    cur, path = current_path(d)
    state = load(path)
    _, _, logs, hl, _, _, bu = state
    if not logs and not bu:
        raise ValueError("Nothing to undo.")
    last = max(logs, key=lambda r: r[5], default=None)
    change = max(bu, key=lambda b: b[0], default=None)
    if change and (last is None or change[0] > last[5]):
        bu.remove(change)
        note = _rewrite(d, cur, path, state)
        _, stamp, legend, old = change
        if legend == ACC_TAG:  # account totals saved without a log entry: put the old ones back
            restore_account(d, old)
            what = ("restored to " + paint(f"KILLS {old[0]:,} | WINS {old[1]:,}")) if old else "removed (not set before)"
            return f"Undone: {stamp} | ACCOUNT {what}  ({note})\n" + _latest_line(logs)
        restore_base(d, legend, old)
        if old:
            t = legend_totals(hl, logs).get(legend, zero())
            what = "restored to " + paint(f"KILLS {old[0] + t[1]:,} | WINS {old[1] + t[2]:,}") + " (all-time)"
        else:
            what = "removed (no base before)"
        return f"Undone: {stamp} | BASE {legend} {what}  ({note})\n" + _latest_line(logs)
    logs.remove(last)
    snap = next((b for b in bu if b[0] == last[5] and b[2] == ACC_TAG), None)  # account gain snapshot
    if snap:
        bu.remove(snap)
    note = _rewrite(d, cur, path, state)
    if snap and snap[3]:  # account gain: the totals go back exactly to what they were before it
        restore_account(d, snap[3])
    elif last[6]:  # only entries that were added to the account totals are taken back out
        bump_account(d, -last[2], -last[3])
    acct = "  [ACCOUNT restored to " + paint(f"KILLS {snap[3][0]:,} | WINS {snap[3][1]:,}") + "]" if snap and snap[3] else ""
    return f"Undone: {_entry_line(last)}  ({note}){acct}\n" + _latest_line(logs)


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
