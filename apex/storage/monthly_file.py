"""Monthly data file (apex_stats_YYYY-MM.txt): render, load and locate the current month.

Header lines (@FILE, @HIST, @PREV, @HL, @PL, @LV) carry the totals of earlier months forward, so
only the newest file is ever read. load() dispatches on the first column and stops at the footer.
"""
import os

from apex.config import AGG, FNAME, FOOTER_MARK, FRE, LEG_W, REF_W, TAG_W
from apex.core.aggregates import ints, zero
from apex.display.tables import SUM_HEAD, summary, vals_cells


def row(tag, ref, vals):
    return f"{tag:<{TAG_W}} | {ref:<{REF_W}} | " + vals_cells(vals)


def pl_row(m, leg, t):
    return f"{'@PL':<{TAG_W}} | {m:<7} | {leg:<{LEG_W}} | " + vals_cells(t)


def lv_row(day, n):
    return f"{'@LV':<{TAG_W}} | {day:<{REF_W}} | {n:>7}"


def log_row(r):
    d, leg, k, w, lv, i, acc = r
    return f"{'L':<{TAG_W}} | {d:<16} | {leg:<{LEG_W}} | {k:>5} | {w:>5} | {lv:>6} | {i:>4} | {acc:>3}"


AGG_NAMES = [n for n, _ in AGG]
LOG_HEAD = (f"{'# LOG':<{TAG_W}} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | "
            f"{'KILLS':>5} | {'WINS':>5} | {'LEVEL':>6} | {'ID':>4} | {'ACC':>3}")
AGG_HEAD = row("# TAG", "REFERENCE", AGG_NAMES)
HL_HEAD = row("# TAG", "LEGEND", AGG_NAMES)
PL_HEAD = f"{'# TAG':<{TAG_W}} | {'MONTH':<7} | {'LEGEND':<{LEG_W}} | " + vals_cells(AGG_NAMES)
LV_HEAD = f"{'# TAG':<{TAG_W}} | {'DAY':<{REF_W}} | {'LEVEL':>7}"
W = max(len(SUM_HEAD), len(AGG_HEAD), len(PL_HEAD), len(LOG_HEAD))


def render(month, hist, prev, logs, hl, pl, lv):
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
    out += ["", eq, LOG_HEAD, dash]
    out += [log_row(r) for r in logs]
    out += ["", eq, summary(month, hist, prev, logs, color=False, sep=False)]  # data files: plain
    return "\n".join(out)


def load(path):
    hist, prev, logs, hl, pl, lv = zero(), [], [], {}, [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            c = line.split("|")
            k = c[0].strip()
            if k == "L":
                lvl = int(c[5]) if len(c) > 5 else 0               # older files: no level column
                lid = int(c[6]) if len(c) > 6 else len(logs) + 1   # older files: no id column
                acc = int(c[7]) if len(c) > 7 else 0               # older files: not in the account
                logs.append((c[1].strip(), c[2].strip(), int(c[3]), int(c[4]), lvl, lid, acc))
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
            elif k == FOOTER_MARK:
                break  # summary is recomputed: no need to read it
    return hist, prev, logs, hl, pl, lv


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
    return cur, os.path.join(d, FNAME.format(cur))
