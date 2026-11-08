"""Table primitives and the match summary, shared by the data-file footer and the reports."""
from datetime import datetime

from apex.config import AGG, DFMT, FOOTER_MARK, LEG_W, REF_W, REP
from apex.core.aggregates import log_agg, periods
from apex.display.colors import green, paint, red, visible_len


def num(v, w=0, sep=True):
    """Right-aligned number with thousands separators (15,000) for the terminal; sep=False
    (data files) keeps plain digits. Non-numbers (table headers) are just aligned."""
    return f"{v:>{w},}" if sep and isinstance(v, int) else f"{v:>{w}}"


def vals_cells(vals, cols=AGG):
    return " | ".join(f"{v:>{w}}" for v, (_, w) in zip(vals, cols))


def rep_cells(t, color=None, sep=True):
    """Report columns only (KILLS red, WINS green): the stored LOGS count is never shown."""
    (_, kw), (_, ww) = REP
    return f"{red(num(t.kills, kw, sep), color)} | {green(num(t.wins, ww, sep), color)}"


def sum_row(label, t, color=None, sep=True):
    return f"{label:<{REF_W}} | " + rep_cells(t, color, sep)


REP_NAMES = [n for n, _ in REP]
SUM_HEAD = f"{'REFERENCE':<{REF_W}} | " + vals_cells(REP_NAMES, REP)
LREP_HEAD = f"{'# LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)
PERIOD_LABELS = ("MONTH {}", "SEMIANNUAL", "ANNUAL", "ALL-TIME")


def side_by_side(left, right, gap=4):
    """Two blocks of lines next to each other; the left one is padded to its widest line."""
    w = max((visible_len(x) for x in left), default=0)
    n = max(len(left), len(right))
    left, right = left + [""] * (n - len(left)), right + [""] * (n - len(right))
    return [x + " " * (w - visible_len(x) + gap) + y if y else x for x, y in zip(left, right)]


def summary(month, hist, prev, logs, color=None, sep=True):
    out = [f"{FOOTER_MARK}  (updated: {datetime.now():{DFMT}})", paint(SUM_HEAD, color), "-" * len(SUM_HEAD)]
    for lbl, t in zip(PERIOD_LABELS, periods(month, log_agg(logs), hist, prev)):
        out.append(sum_row(lbl.format(month), t, color, sep))
    out.append("=" * len(SUM_HEAD))
    return "\n".join(out) + "\n"
