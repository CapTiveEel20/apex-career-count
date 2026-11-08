"""Monthly data file (apex_stats_YYYY-MM.txt): render, load, locate, roll over and write a month.

Header lines (@FILE, @HIST, @PREV, @HL, @PL, @LV, @LL, @TK) carry the totals of earlier months forward, so
only the newest file is ever read. @BU lines are the undo records (Change) of this file's base and
account changes (target @ACCOUNT = the global account totals before the change).
load() dispatches on the first column and stops at the footer.
"""
import os
from datetime import timedelta

from apex.config import (AGG, DAY_FMT, FNAME, FOOTER_MARK, FRE, LEG_W, LV_KEEP_DAYS, REF_W, SRC_LEVEL, SRC_MATCH,
                         TAG_W, YEAR_MONTHS)
from apex.core.aggregates import (day_levels, ints, last_logged, legend_agg, log_agg, midx, top_matches, vadd,
                                  zero)
from apex.core.levels import prune_lv
from apex.core.records import Change, Entry, Month
from apex.display.tables import SUM_HEAD, summary, vals_cells
from apex.storage.atomic import write_atomic


def row(tag, ref, vals):
    return f"{tag:<{TAG_W}} | {ref:<{REF_W}} | " + vals_cells(vals)


def pl_row(m, leg, t):
    return f"{'@PL':<{TAG_W}} | {m:<7} | {leg:<{LEG_W}} | " + vals_cells(t)


def lv_row(day, n):
    return f"{'@LV':<{TAG_W}} | {day:<{REF_W}} | {n:>7}"


def ll_row(leg, day):
    return f"{'@LL':<{TAG_W}} | {leg:<{REF_W}} | {day}"


def tk_row(r):
    day, leg, k, w = r
    return f"{'@TK':<{TAG_W}} | {day:<16} | {leg:<{LEG_W}} | {k:>5} | {w:>5}"


def bu_row(c):
    k, w, upd = c.old if c.old else ("-", "-", "-")
    return f"{'@BU':<{TAG_W}} | {c.id:>4} | {c.date:<16} | {c.target:<{LEG_W}} | {k:>9} | {w:>8} | {upd}"


def log_row(e):
    return (f"{'L':<{TAG_W}} | {e.date:<16} | {e.legend:<{LEG_W}} | {e.kills:>5} | {e.wins:>5} | "
            f"{e.level:>6} | {e.id:>4} | {e.acc:>3} | {e.src:>3}")


AGG_NAMES = [n for n, _ in AGG]
LOG_HEAD = (f"{'# LOG':<{TAG_W}} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | "
            f"{'KILLS':>5} | {'WINS':>5} | {'LEVEL':>6} | {'ID':>4} | {'ACC':>3} | {'SRC':>3}")
AGG_HEAD = row("# TAG", "REFERENCE", AGG_NAMES)
HL_HEAD = row("# TAG", "LEGEND", AGG_NAMES)
PL_HEAD = f"{'# TAG':<{TAG_W}} | {'MONTH':<7} | {'LEGEND':<{LEG_W}} | " + vals_cells(AGG_NAMES)
LV_HEAD = f"{'# TAG':<{TAG_W}} | {'DAY':<{REF_W}} | {'LEVEL':>7}"
LL_HEAD = f"{'# TAG':<{TAG_W}} | {'LEGEND':<{REF_W}} | LAST MATCH"
TK_HEAD = f"{'# TAG':<{TAG_W}} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | {'KILLS':>5} | {'WINS':>5}"
BU_HEAD = (f"{'# TAG':<{TAG_W}} | {'ID':>4} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | "
           f"{'OLD KILLS':>9} | {'OLD WINS':>8} | OLD UPDATED")
W = max(len(SUM_HEAD), len(AGG_HEAD), len(PL_HEAD), len(LOG_HEAD))


def render(month, m):
    """The text of month's file holding the Month m."""
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
        row("@HIST", f"< {month}", m.hist),
    ]
    out += [row("@PREV", mo, t) for mo, t in m.prev]
    out += ["", "# @HL = all-time totals per legend (previous months)", HL_HEAD, dash]
    out += [row("@HL", leg, m.hl[leg]) for leg in sorted(m.hl)]
    out += ["", "# @PL = per-month, per-legend totals (last 11 months)", PL_HEAD, dash]
    out += [pl_row(mo, leg, t) for mo, leg, t in m.pl]
    out += ["", "# @LV = last level recorded per day (previous months)", LV_HEAD, dash]
    out += [lv_row(day, n) for day, n in m.lv]
    out += ["", "# @LL = date and time of the last match logged per legend (previous months)", LL_HEAD, dash]
    out += [ll_row(leg, m.ll[leg]) for leg in sorted(m.ll)]
    out += ["", "# @TK = all-time highest-kill matches (previous months), best first", TK_HEAD, dash]
    out += [tk_row(r) for r in m.top]
    if m.changes:  # only months with base or account changes have this section
        out += ["", "# @BU = base / @ACCOUNT changes of this month (undo puts the OLD values back; - = none)",
                BU_HEAD, dash]
        out += [bu_row(c) for c in m.changes]
    out += ["", eq, LOG_HEAD, dash]
    out += [log_row(e) for e in m.logs]
    out += ["", eq, summary(month, m.hist, m.prev, m.logs, color=False, sep=False)]  # data files: plain
    return "\n".join(out)


def _entry(c, n):
    """Entry of an L line split into cells c; n = entries read so far. Older files lack the later
    columns: no level = not recorded, no ID = file order, no ACC = not in the account totals, no
    SRC = a level-only update if it has only a level, a match otherwise."""
    kills, wins = int(c[3]), int(c[4])
    lvl = int(c[5]) if len(c) > 5 else 0
    lid = int(c[6]) if len(c) > 6 else n + 1
    acc = int(c[7]) if len(c) > 7 else 0
    if len(c) > 8:
        src = c[8].strip()
    else:
        src = SRC_LEVEL if not kills and not wins and lvl else SRC_MATCH
    return Entry(c[1].strip(), c[2].strip(), kills, wins, lvl, lid, acc, src)


def load(path):
    """The Month held by one monthly file."""
    m = Month.empty()
    with open(path, encoding="utf-8") as f:
        for line in f:
            c = line.split("|")
            k = c[0].strip()
            if k == "L":
                m.logs.append(_entry(c, len(m.logs)))
            elif k == "@HIST":
                m.hist[:] = ints(c[2:])
            elif k == "@PREV":
                m.prev.append((c[1].strip(), ints(c[2:])))
            elif k == "@HL":
                m.hl[c[1].strip()] = ints(c[2:])
            elif k == "@PL":
                m.pl.append((c[1].strip(), c[2].strip(), ints(c[3:])))
            elif k == "@LV":
                m.lv.append((c[1].strip(), int(c[2])))
            elif k == "@LL":
                m.ll[c[1].strip()] = c[2].strip()
            elif k == "@TK":
                m.top.append((c[1].strip(), c[2].strip(), int(c[3]), int(c[4])))
            elif k == "@BU":
                old = None if c[4].strip() == "-" else (int(c[4]), int(c[5]), c[6].strip())
                m.changes.append(Change(int(c[1]), c[2].strip(), c[3].strip(), old))
            elif k == FOOTER_MARK:
                break  # summary is recomputed: no need to read it
    return m


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


def load_current(d):
    """(month, path, Month) of the newest file (1 read); ValueError if there is none."""
    cur = current_month(d)
    if not cur:
        raise ValueError("No data recorded yet.")
    path = month_path(d, cur)
    return cur, path, load(path)


def write_month(d, month, m):
    """Write month's file holding m (1 atomic write); returns its path."""
    path = month_path(d, month)
    write_atomic(path, render(month, m))
    return path


def save_change(d, month, m, stamp, target, old):
    """Record an undoable change that logs nothing (a base set, corrected or removed, or the first
    account save): its Change goes into month's file, written now, before the caller updates
    account_stats.txt. old = the value being replaced (None = there was none)."""
    m.changes.append(Change(m.next_id(), stamp, target, old))
    write_month(d, month, m)


def read_month(d, month, any_month=False):
    """(cur, month, Month) for a record of `month`: cur = newest file ('' if none), Month = its
    contents (1 read). An older month than cur is closed: ValueError, unless any_month (undated
    records such as base changes go into cur)."""
    os.makedirs(d, exist_ok=True)
    cur = current_month(d)
    if month < cur:
        if not any_month:
            raise ValueError(f"Error: month {month} is already closed (current file: {cur}).")
        month = cur
    return cur, month, load(month_path(d, cur)) if cur else Month.empty()


def roll_over(cur, month, day, m):
    """Month of the new file `month` (newer than cur): the totals of cur are carried into its
    header, and its log entries and changes start empty. day = date of the new record."""
    ni = midx(month)
    keep = lambda mo: ni - midx(mo) < YEAR_MONTHS
    hist = vadd(m.hist, log_agg(m.logs))
    prev = [(mo, v) for mo, v in m.prev + [(cur, log_agg(m.logs))] if keep(mo)]
    la = legend_agg(m.logs)
    hl = dict(m.hl)
    for leg, t in la.items():
        hl[leg] = vadd(hl.get(leg, zero()), t)
    pl = [x for x in m.pl + [(cur, leg, la[leg]) for leg in sorted(la)] if keep(x[0])]
    cutoff = (day - timedelta(days=LV_KEEP_DAYS)).strftime(DAY_FMT)
    lv = prune_lv(m.lv + sorted(day_levels(m.logs).items()), cutoff)
    return Month(hist, prev, [], hl, pl, lv, [], last_logged(m.ll, m.logs), top_matches(m.top, m.logs))


def open_month(d, dt, any_month=False):
    """(month, Month) of the file a record dated dt goes into, rolled over if it is a new month
    (nothing is written here)."""
    cur, month, m = read_month(d, dt.strftime("%Y-%m"), any_month)
    if cur and month > cur:
        m = roll_over(cur, month, dt.date(), m)
    return month, m
