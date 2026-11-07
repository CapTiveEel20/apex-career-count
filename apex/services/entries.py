"""The single save path (save_log) and its wrappers, plus the LIFO undo."""
import os
from datetime import timedelta

from apex.config import DAY_FMT, DFMT, FNAME, LEG_W, LV_KEEP_DAYS, YEAR_MONTHS
from apex.core.aggregates import day_levels, legend_agg, log_agg, midx, vadd, zero
from apex.core.levels import check_level, last_level, prune_lv
from apex.core.parsing import LEVEL_RE, QUICK_RE, clean, parse_when
from apex.display.colors import paint
from apex.display.messages import logs_word
from apex.display.tables import summary
from apex.storage.account_file import bump_account, load_account, save_account
from apex.storage.atomic import write_atomic
from apex.storage.monthly_file import current_month, current_path, load, render


def save_log(d, kills, wins, legend=None, when=None, level=0, delta=None, account=None):
    """Save one log entry (1 read + 1 atomic write). Errors -> ValueError.
    level = absolute level (0 = not recorded); delta (from "+<n>") = last level recorded
    before the entry's date + delta. Either way the level check runs.
    account = account totals already loaded by the caller (account_cmd), so they are not read twice."""
    if kills < 0 or wins < 0 or level < 0:
        raise ValueError("Error: kills, wins and level cannot be negative.")
    if delta is not None and delta < 1:
        raise ValueError("Error: a +<n> level increment must be 1 or higher.")
    dt = parse_when(when)
    stamp, month = dt.strftime(DFMT), dt.strftime("%Y-%m")

    os.makedirs(d, exist_ok=True)
    cur = current_month(d)
    if month < cur:
        raise ValueError(f"Error: month {month} is already closed (current file: {cur}).")
    if cur:
        hist, prev, logs, hl, pl, lv = load(os.path.join(d, FNAME.format(cur)))
    else:
        hist, prev, logs, hl, pl, lv = zero(), [], [], {}, [], []
    if delta is not None:
        base = last_level(stamp, logs, lv)
        if not base:
            raise ValueError("Error: no level recorded yet; enter an absolute level first (e.g. 700).")
        level = base + delta
    check_level(level, stamp, logs, lv)

    if cur and month > cur:  # new month -> new file, totals carried into the header
        ni = midx(month)
        keep = lambda m: ni - midx(m) < YEAR_MONTHS
        hist = vadd(hist, log_agg(logs))
        prev = [(m, v) for m, v in prev + [(cur, log_agg(logs))] if keep(m)]
        la = legend_agg(logs)
        for leg, t in la.items():
            hl[leg] = vadd(hl.get(leg, zero()), t)
        pl = [x for x in pl + [(cur, leg, la[leg]) for leg in sorted(la)] if keep(x[0])]
        cutoff = (dt.date() - timedelta(days=LV_KEEP_DAYS)).strftime(DAY_FMT)
        lv = prune_lv(lv + sorted(day_levels(logs).items()), cutoff)
        logs = []

    acc = (account or load_account(d)) if (kills or wins) else None  # totals to bump (None = unset / nothing to add)
    rec = (stamp, clean(legend, LEG_W), kills, wins, level, max((r[5] for r in logs), default=0) + 1,
           1 if acc else 0)
    logs.append(rec)
    logs.sort(key=lambda r: (r[0], r[5]))
    path = os.path.join(d, FNAME.format(month))
    write_atomic(path, render(month, hist, prev, logs, hl, pl, lv))
    if acc:  # keep the global account totals in step with the logs (after the monthly file)
        save_account(d, acc[0] + kills, acc[1] + wins)
    return path, summary(month, hist, prev, logs), len(logs), rec


def undo(d):
    """Remove the most recently added entry (LIFO). An emptied month file is deleted, so the
    previous month (left untouched at rollover) becomes current again."""
    cur, path = current_path(d)
    hist, prev, logs, hl, pl, lv = load(path)
    if not logs:
        raise ValueError("Nothing to undo.")
    last = max(logs, key=lambda r: r[5])
    logs.remove(last)
    if logs:
        write_atomic(path, render(cur, hist, prev, logs, hl, pl, lv))
        note = f"{logs_word(len(logs))} left in {cur}"
    else:
        os.remove(path)
        note = f"{cur} is now empty, file removed; current month: {current_month(d) or 'none'}"
    if last[6]:  # only entries that were added to the account totals are taken back out
        bump_account(d, -last[2], -last[3])
    return (f"Undone: {last[0]} | {last[1]} | " + paint(f"WINS {last[3]:,} | KILLS {last[2]:,}") +
            f" | LEVEL {last[4]:,}  ({note})\n")


def save_level(d, token, when=None):
    """Level-only entry (wins/kills = 0): "700" = absolute level, "+5" = last level + 5.
    Always goes through save_log, so the level check runs."""
    if not LEVEL_RE.match(token):
        raise ValueError("Format: <n> (e.g. 700) or <n>l (e.g. 3l)")
    n = int(token)
    if n < 1:
        raise ValueError("Error: the level (or <n>l) must be 1 or higher.")
    if token.startswith("+"):
        return save_log(d, 0, 0, None, when, 0, delta=n)
    return save_log(d, 0, 0, None, when, n)


def save_quick(d, token, when=None):
    """Single-token entries: "<n>" = absolute level, "<n>l" / "+<n>" = n more levels,
    "<n>k" = n kills only, "<n>w" = n wins only. Quick kills/wins never carry a legend."""
    m = QUICK_RE.match(token)
    if not m:
        return save_level(d, token, when)
    n, kind = int(m.group(1)), m.group(2).lower()
    if n < 1:
        raise ValueError("Error: <n>k, <n>w and <n>l need n of 1 or higher.")
    if kind == "l":
        return save_level(d, f"+{n}", when)
    return save_log(d, n, 0, None, when) if kind == "k" else save_log(d, 0, n, None, when)
