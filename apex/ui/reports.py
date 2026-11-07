"""Read-only views: report, l, k, w, m, lv, log, logl (each reads the current file once)."""
from datetime import date, timedelta

from apex.config import DAY_FMT, LEG_W, NO_LEGEND, REF_W, REP, SRC_MATCH
from apex.core.aggregates import legend_agg, legend_periods, log_agg, months_ago
from apex.display.colors import green, orange, paint, red
from apex.display.messages import account_line
from apex.display.tables import LREP_HEAD, REP_NAMES, num, rep_cells, side_by_side, summary, vals_cells
from apex.storage.account_file import load_acct, load_account
from apex.storage.monthly_file import current_path, load

TOP_N = 3
TOP_HEAD = f"{'#':<2} | {'LEGEND':<{LEG_W}} | {'KILLS':>8}"


def top_legends(logs, n=TOP_N):
    """The n legends with the most kills logged in this file: [(legend, [logs, kills, wins])].
    Ties: more wins first, then by name. Legends with no kills this month are left out."""
    rows = [(leg, t) for leg, t in legend_agg(logs).items() if leg != NO_LEGEND and t[1] > 0]
    rows.sort(key=lambda x: (-x[1][1], -x[1][2], x[0]))
    return rows[:n]


def legend_report(month, logs, hl, pl, bases):
    """'l': two tables side by side. Left: every legend set with 'base' and its all-time totals
    (base + logged entries), kills and wins only, no grand total. Right: the TOP_N legends by
    kills logged in the current month."""
    dash = "-" * len(LREP_HEAD)
    left = ["# ALL-TIME BY LEGEND  (base + logged)", paint(LREP_HEAD), dash]
    rows = [(leg, ps) for leg, ps in legend_periods(month, logs, hl, pl, bases) if leg in bases]
    for leg, ps in rows:
        left.append(f"{leg:<{LEG_W}} | " + rep_cells(ps[3]))
    if not rows:
        left.append("(no base legends yet)")
    left.append("=" * len(LREP_HEAD))
    tdash = "-" * len(TOP_HEAD)
    right = [f"# TOP {TOP_N} THIS MONTH  ({month})", paint(TOP_HEAD), tdash]
    top = top_legends(logs)
    for i, (leg, t) in enumerate(top, 1):
        right.append(f"{i:<2} | {leg:<{LEG_W}} | " + red(num(t[1], 8)))
    if not top:
        right.append("(no kills this month)")
    right.append("=" * len(TOP_HEAD))
    return "\n".join(side_by_side(left, right)) + "\n"


STAT_COLS = (("MONTH", 8), ("SEMIANNUAL", 10), ("ANNUAL", 8), ("ALL-TIME", 8))
STAT_HEAD = f"{'# LEGEND':<{LEG_W}} | " + vals_cells([n for n, _ in STAT_COLS], STAT_COLS)


def stat_report(month, logs, hl, pl, idx, name, bases=None):
    """One stat (idx 1 = kills, 2 = wins) per legend: monthly, semiannual, annual, all-time
    (all-time includes the legend's base)."""
    dash = "-" * len(STAT_HEAD)
    fn = red if idx == 1 else green  # kills red, wins green

    def cells(vals):
        return " | ".join(fn(num(v, w)) for v, (_, w) in zip(vals, STAT_COLS))

    head = f"{'# LEGEND':<{LEG_W}} | " + cells([n for n, _ in STAT_COLS])
    out = [paint(f"# {name} BY LEGEND") + f"  (current month: {month})", head, dash]
    rows = legend_periods(month, logs, hl, pl, bases)
    total = [0] * len(STAT_COLS)
    for leg, ps in rows:
        vals = [t[idx] for t in ps]
        total = [a + b for a, b in zip(total, vals)]
        out.append(f"{leg:<{LEG_W}} | " + cells(vals))
    if rows:  # combined across all legends; ALL-TIME = absolute historical total
        out += [dash, f"{'GRAND TOTAL':<{LEG_W}} | " + cells(total)]
    else:
        out.append("(no legends recorded yet)")
    out.append("=" * len(STAT_HEAD))
    return "\n".join(out) + "\n"


def lv_report(logs, lv):
    today = date.today()
    end = today.strftime(DAY_FMT)
    # (day or timestamp, level): carried days + every current-month entry, so gains within a
    # single day are counted too. Levels never decrease, so sorting by time also sorts by level.
    points = sorted(x for x in lv + [(r[0], r[4]) for r in logs if r[4]] if x[0][:10] <= end)
    current = points[-1][1] if points else 0
    windows = (("1 WEEK", today - timedelta(days=7)), ("1 MONTH", months_ago(today, 1)),
               ("3 MONTHS", months_ago(today, 3)), ("6 MONTHS", months_ago(today, 6)),
               ("1 YEAR", months_ago(today, 12)))
    head = f"{'PERIOD':<{REF_W}} | {'FROM':<10} | "
    width = len(head) + 7
    cur_txt = f"{current:,}" if current else "-"
    out = [f"# LEVELS GAINED  (today: {end}, " + orange(f"current level: {cur_txt}") + ")",
           head + " " + orange("GAINED"), "-" * width]
    for label, start in windows:
        s = start.strftime(DAY_FMT)
        base = [n for k, n in points if k[:10] <= s]
        inside = [n for k, n in points if k[:10] > s]
        gained = current - (base[-1] if base else inside[0]) if points and (base or inside) else 0
        out.append(f"{label:<{REF_W}} | {s:<10} | " + orange(num(gained, 7)))
    out.append("=" * width)
    return "\n".join(out) + "\n"


def report_text(d):
    """Match summaries first, then the level report (one read of the current file)."""
    cur, path = current_path(d)
    hist, prev, logs, _, _, lv, _ = load(path)
    return (f"File: {path}\n\n" + account_line(load_account(d)) + "\n" +
            summary(cur, hist, prev, logs) + "\n" + lv_report(logs, lv))


def legend_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl, _, _ = load(path)
    return f"File: {path}\n\n" + legend_report(cur, logs, hl, pl, load_acct(d)[1])


def kills_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl, _, _ = load(path)
    acc, bases = load_acct(d)
    return account_line(acc, "kills") + "\n" + stat_report(cur, logs, hl, pl, 1, "KILLS", bases)


def wins_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl, _, _ = load(path)
    acc, bases = load_acct(d)
    return account_line(acc, "wins") + "\n" + stat_report(cur, logs, hl, pl, 2, "WINS", bases)


def m_text(d):
    cur, path = current_path(d)
    t = log_agg(load(path)[2])
    return f"MONTH {cur}  |  " + paint(f"KILLS {t[1]:,}  |  WINS {t[2]:,}") + "\n"


def lv_text(d):
    _, path = current_path(d)
    _, _, logs, _, _, lv, _ = load(path)
    return lv_report(logs, lv)


MLOG_HEAD = f"{'DATE':<16} | {'LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)


def match_log(month, logs):
    """'log': every match entry of the current file, oldest first. Entries logged by an
    account or base update (SRC A / B) and level-only updates (SRC L) are left out."""
    dash = "-" * len(MLOG_HEAD)
    out = [f"# MATCH LOG  (month {month}; account and base updates excluded)", paint(MLOG_HEAD), dash]
    rows = [r for r in logs if r[7] == SRC_MATCH]
    for r in rows:
        out.append(f"{r[0]:<16} | {r[1]:<{LEG_W}} | " + rep_cells([0, r[2], r[3]]))
    if not rows:
        out.append("(no matches logged this month)")
    out.append("=" * len(MLOG_HEAD))
    return "\n".join(out) + "\n"


LLOG_HEAD = f"{'DATE':<16} | {'LEVEL':>7} | {'CHANGE':>7}"


def level_log(month, logs, lv):
    """'logl': every recorded level, oldest first: the carried @LV days of earlier months (highest
    level per day) and each current-month entry with a level, with the change from the row before."""
    dash = "-" * len(LLOG_HEAD)
    out = [f"# LEVEL HISTORY  (month {month}; earlier months: highest level per day)", LLOG_HEAD, dash]
    prev = None
    for when, n in list(lv) + [(r[0], r[4]) for r in logs if r[4]]:
        change = f"{n - prev:+,}" if prev is not None else "-"
        out.append(f"{when:<16} | " + orange(num(n, 7)) + " | " + orange(f"{change:>7}"))
        prev = n
    if prev is None:
        out.append("(no level recorded yet)")
    out.append("=" * len(LLOG_HEAD))
    return "\n".join(out) + "\n"


def log_text(d):
    cur, path = current_path(d)
    return match_log(cur, load(path)[2])


def logl_text(d):
    cur, path = current_path(d)
    _, _, logs, _, _, lv, _ = load(path)
    return level_log(cur, logs, lv)


VIEWS = {"report": report_text, "l": legend_text, "k": kills_text, "w": wins_text,
         "m": m_text, "lv": lv_text, "log": log_text, "logl": logl_text}
