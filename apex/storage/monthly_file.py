"""Monthly data file (apex_stats_YYYY-MM.txt): render, load, locate and roll over the current month.

Header lines (@FILE, @HIST, @PREV, @HL, @PL, @LV) carry the totals of earlier months forward, so
only the newest file is ever read. @BU lines are the undo records of this file's base and account
changes (legend @ACCOUNT = the global account totals before the change).
load() dispatches on the first column and stops at the footer.
"""
import os
from datetime import timedelta

from apex.config import (AGG, DAY_FMT, FNAME, FOOTER_MARK, FRE, LEG_W, LV_KEEP_DAYS, REF_W, SRC_LEVEL, SRC_MATCH,
                         TAG_W, YEAR_MONTHS)
from apex.core.aggregates import day_levels, ints, legend_agg, log_agg, midx, vadd, zero
from apex.core.levels import prune_lv
from apex.display.tables import SUM_HEAD, summary, vals_cells

# Base change (undo record): (id, date, legend, old) with old = (kills, wins, updated) or None


def row(tag, ref, vals):
    return f"{tag:<{TAG_W}} | {ref:<{REF_W}} | " + vals_cells(vals)


def pl_row(m, leg, t):
    return f"{'@PL':<{TAG_W}} | {m:<7} | {leg:<{LEG_W}} | " + vals_cells(t)


def lv_row(day, n):
    return f"{'@LV':<{TAG_W}} | {day:<{REF_W}} | {n:>7}"


def bu_row(b):
    i, stamp, leg, old = b
    k, w, upd = old if old else ("-", "-", "-")
    return f"{'@BU':<{TAG_W}} | {i:>4} | {stamp:<16} | {leg:<{LEG_W}} | {k:>9} | {w:>8} | {upd}"


def log_row(r):
    d, leg, k, w, lv, i, acc, src = r
    return (f"{'L':<{TAG_W}} | {d:<16} | {leg:<{LEG_W}} | {k:>5} | {w:>5} | {lv:>6} | {i:>4} | {acc:>3}"
            f" | {src:>3}")


AGG_NAMES = [n for n, _ in AGG]
LOG_HEAD = (f"{'# LOG':<{TAG_W}} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | "
            f"{'KILLS':>5} | {'WINS':>5} | {'LEVEL':>6} | {'ID':>4} | {'ACC':>3} | {'SRC':>3}")
AGG_HEAD = row("# TAG", "REFERENCE", AGG_NAMES)
HL_HEAD = row("# TAG", "LEGEND", AGG_NAMES)
PL_HEAD = f"{'# TAG':<{TAG_W}} | {'MONTH':<7} | {'LEGEND':<{LEG_W}} | " + vals_cells(AGG_NAMES)
LV_HEAD = f"{'# TAG':<{TAG_W}} | {'DAY':<{REF_W}} | {'LEVEL':>7}"
BU_HEAD = (f"{'# TAG':<{TAG_W}} | {'ID':>4} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | "
           f"{'OLD KILLS':>9} | {'OLD WINS':>8} | OLD UPDATED")
W = max(len(SUM_HEAD), len(AGG_HEAD), len(PL_HEAD), len(LOG_HEAD))


def render(month, hist, prev, logs, hl, pl, lv, bu=()):
    eq, dash = "=" * W, "-" * W
    out = [
        eq,
        "  APEX LEGENDS - STATS LOG",
        f"  MONTH {month}",
        eq,
        f"{'@FILE':<{TAG_W}} | {month}",
        "# @HIST = all-time totals of previous months",
        "# @PREV = per-month totals (last 11 months)",
        AGG_HEAD,
        dash,
        row("@HIST", f"< {month}", hist),
    ]
    out += [row("@PREV", m, t) for m, t in prev]
    out += ["", "# @HL = all-time totals per legend (previous months)", HL_HEAD, dash]
    out += [row("@HL", leg, hl[leg]) for leg in sorted(hl)]
    out += ["", "# @PL = per-month, per-legend totals (last 11 months)", PL_HEAD, dash]
    out += [pl_row(m, leg, t) for m, leg, t in pl]
    out += ["", "# @LV = highest level reached per day (previous months)", LV_HEAD, dash]
    out += [lv_row(day, n) for day, n in lv]
    if bu:  # only months with base or account changes have this section
        out += ["", "# @BU = base / @ACCOUNT changes of this month (undo puts the OLD values back; - = none)", BU_HEAD, dash]
        out += [bu_row(b) for b in bu]
    out += ["", eq, LOG_HEAD, dash]
    out += [log_row(r) for r in logs]
    out += ["", eq, summary(month, hist, prev, logs, color=False, sep=False)]  # data files: plain
    return "\n".join(out)


def load(path):
    """(hist, prev, logs, hl, pl, lv, bu) of one monthly file."""
    hist, prev, logs, hl, pl, lv, bu = zero(), [], [], {}, [], [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            c = line.split("|")
            k = c[0].strip()
            if k == "L":
                lvl = int(c[5]) if len(c) > 5 else 0               # older files: no level column
                lid = int(c[6]) if len(c) > 6 else len(logs) + 1   # older files: no id column
                acc = int(c[7]) if len(c) > 7 else 0               # older files: not in the account
                kills, wins = int(c[3]), int(c[4])
                if len(c) > 8:
                    src = c[8].strip()
                else:  # older files: no source column; level-only updates are told apart, the rest are matches
                    src = SRC_LEVEL if not kills and not wins and lvl else SRC_MATCH
                logs.append((c[1].strip(), c[2].strip(), kills, wins, lvl, lid, acc, src))
            elif k == "@HIST":
                hist = ints(c[2:])
            elif k == "@PREV":
                prev.append((c[1].strip(), ints(c[2:])))
            elif k == "@HL":
                hl[c[1].strip()] = ints(c[2:])
            elif k == "@PL":
                pl.append((c[1].strip(), c[2].strip(), ints(c[3:])))
            elif k == "@LV":
                lv.append((c[1].strip(), int(c[2])))
            elif k == "@BU":
                old = None if c[4].strip() == "-" else (int(c[4]), int(c[5]), c[6].strip())
                bu.append((int(c[1]), c[2].strip(), c[3].strip(), old))
            elif k == FOOTER_MARK:
                break  # summary is recomputed: no need to read it
    return hist, prev, logs, hl, pl, lv, bu


def month_path(d, month):
    return os.path.join(d, FNAME.format(month))


def current_month(d):
    best = ""
    if os.path.isdir(d):
        for name in os.listdir(d):
            m = FRE.match(name)
            if m and m.group(1) > best:
                best = m.group(1)
    return best


def current_path(d):
    cur = current_month(d)
    if not cur:
        raise ValueError("No data recorded yet.")
    return cur, month_path(d, cur)


def next_id(logs, bu):
    """Undo-stack ID for a new record: one above every log entry and base change of the file."""
    return max([r[5] for r in logs] + [b[0] for b in bu], default=0) + 1


def read_month(d, month, any_month=False):
    """(cur, month, state) for a record of `month`: cur = newest file ('' if none), state =
    (hist, prev, logs, hl, pl, lv, bu) of that file (1 read). An older month than cur is closed:
    ValueError, unless any_month (undated records such as base changes go into cur)."""
    os.makedirs(d, exist_ok=True)
    cur = current_month(d)
    if month < cur:
        if not any_month:
            raise ValueError(f"Error: month {month} is already closed (current file: {cur}).")
        month = cur
    if cur:
        state = load(month_path(d, cur))
    else:
        state = zero(), [], [], {}, [], [], []
    return cur, month, state


def roll_over(cur, month, day, state):
    """State of the new file `month` (newer than cur): the totals of cur are carried into its
    header and its log entries and base changes start empty. day = date of the new record."""
    hist, prev, logs, hl, pl, lv, _ = state
    ni = midx(month)
    keep = lambda m: ni - midx(m) < YEAR_MONTHS
    hist = vadd(hist, log_agg(logs))
    prev = [(m, v) for m, v in prev + [(cur, log_agg(logs))] if keep(m)]
    la = legend_agg(logs)
    for leg, t in la.items():
        hl[leg] = vadd(hl.get(leg, zero()), t)
    pl = [x for x in pl + [(cur, leg, la[leg]) for leg in sorted(la)] if keep(x[0])]
    cutoff = (day - timedelta(days=LV_KEEP_DAYS)).strftime(DAY_FMT)
    lv = prune_lv(lv + sorted(day_levels(logs).items()), cutoff)
    return hist, prev, [], hl, pl, lv, []


def open_month(d, dt, any_month=False):
    """(month, state) of the file a record dated dt goes into, rolled over if it is a new month
    (nothing is written here)."""
    cur, month, state = read_month(d, dt.strftime("%Y-%m"), any_month)
    if cur and month > cur:
        state = roll_over(cur, month, dt.date(), state)
    return month, state
