"""Read-only views: report, l / lw / la / lm / ls <name>, k, w, m, lv, log, logl (each reads the current
file once)."""
from datetime import date, timedelta

from apex.config import DAY_FMT, LEG_W, NO_LEGEND, REF_W, REP, SRC_MATCH, TOP_MATCHES
from apex.core.aggregates import last_logged, legend_agg, legend_periods, log_agg, months_ago, top_matches
from apex.display.colors import green, orange, paint, red
from apex.display.messages import account_line
from apex.display.tables import LREP_HEAD, REP_NAMES, num, rep_cells, side_by_side, summary, vals_cells
from apex.storage.account_file import load_acct, load_account
from apex.storage.monthly_file import load_current

TOP_N = 3
TOP_HEAD = f"{'#':<2} | {'LEGEND':<{LEG_W}} | {'KILLS':>8}"
LAST_HEAD = LREP_HEAD + f" | {'LAST MATCH':<16}"
# 'l' left-column orders: (key(row, last), highest first?). k = all-time kills, w = all-time wins,
# a = by name, m = last match (most recent first; never played = "" = at the bottom). Ties keep name order.
L_SORTS = {"k": (lambda x, last: x[1][3][1], True), "w": (lambda x, last: x[1][3][2], True),
           "a": (lambda x, last: x[0].lower(), False), "m": (lambda x, last: last.get(x[0], ""), True)}


def top_legends(logs, n=TOP_N):
    """The n legends with the most kills logged in this file: [(legend, [logs, kills, wins])].
    Ties: more wins first, then by name. Legends with no kills this month are left out."""
    rows = [(leg, t) for leg, t in legend_agg(logs).items() if leg != NO_LEGEND and t[1] > 0]
    rows.sort(key=lambda x: (-x[1][1], -x[1][2], x[0]))
    return rows[:n]


def legend_report(month, logs, hl, pl, bases, ll=None, sort="k", search=None):
    """'l': two tables side by side. Left: every legend set with 'base' and its all-time totals
    (base + logged entries), kills and wins only, no grand total, with the date and time of its
    last logged match (ll = carried @LL values; '-' = none yet). sort = a key of L_SORTS (ties keep
    name order); search = only the legends whose name contains it (any case).
    Right: the TOP_N legends by kills logged in the current month (never filtered)."""
    dash = "-" * len(LAST_HEAD)
    left = ["# ALL-TIME BY LEGEND  (base + logged)", paint(LAST_HEAD), dash]
    rows = [(leg, ps) for leg, ps in legend_periods(month, logs, hl, pl, bases) if leg in bases]
    if search:
        rows = [x for x in rows if search.lower() in x[0].lower()]
    last = last_logged(ll or {}, logs)
    key, desc = L_SORTS[sort]
    rows.sort(key=lambda x: key(x, last), reverse=desc)  # stable, also when reversed
    for leg, ps in rows:
        left.append(f"{leg:<{LEG_W}} | " + rep_cells(ps[3]) + f" | {last.get(leg, '-')}")
    if not rows:
        left.append(f"(no base legend matches '{search[:LEG_W]}')" if search and bases else "(no base legends yet)")
    left.append("=" * len(LAST_HEAD))
    tdash = "-" * len(TOP_HEAD)
    right = [f"# TOP {TOP_N} THIS MONTH  ({month})", paint(TOP_HEAD), tdash]
    top = top_legends(logs)
    for i, (leg, t) in enumerate(top, 1):
        right.append(f"{i:<2} | {leg:<{LEG_W}} | " + red(num(t[1], 8)))
    if not top:
        right.append("(no kills this month)")
    right.append("=" * len(TOP_HEAD))
    return "\n".join(side_by_side(left, right, gap=3)) + "\n"  # gap 3 keeps the report compact (85 columns)


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
    # single day are counted too. Sorted by time only: same-minute entries stay in ID order.
    points = sorted((x for x in lv + [(e.date, e.level) for e in logs if e.level] if x[0][:10] <= end),
                    key=lambda x: x[0])
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
    cur, path, m = load_current(d)
    return (f"File: {path}\n\n" + account_line(load_account(d)) + "\n" +
            summary(cur, m.hist, m.prev, m.logs) + "\n" + lv_report(m.logs, m.lv))


def legend_text(d, sort="k", search=None):
    """'l' (by kills), 'lw' (by wins), 'la' (by name), 'lm' (by last match); 'ls <name>' = search
    (by kills). sort = a key of L_SORTS."""
    cur, path, m = load_current(d)
    return (f"File: {path}\n\n" +
            legend_report(cur, m.logs, m.hl, m.pl, load_acct(d)[1], m.ll, sort, search))


def kills_text(d):
    cur, _, m = load_current(d)
    acc, bases = load_acct(d)
    return account_line(acc, "kills") + "\n" + stat_report(cur, m.logs, m.hl, m.pl, 1, "KILLS", bases)


def wins_text(d):
    cur, _, m = load_current(d)
    acc, bases = load_acct(d)
    return account_line(acc, "wins") + "\n" + stat_report(cur, m.logs, m.hl, m.pl, 2, "WINS", bases)


BEST_HEAD = f"{'#':<2} | {'DATE':<16} | {'LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)


def best_matches(top):
    """The all-time leaderboard of single matches by kills (rows from top_matches)."""
    dash = "-" * len(BEST_HEAD)
    out = [paint(f"# TOP {TOP_MATCHES} ALL-TIME HIGHEST KILL MATCHES"), paint(BEST_HEAD), dash]
    for i, (day, leg, k, w) in enumerate(top, 1):
        out.append(f"{i:<2} | {day:<16} | {leg:<{LEG_W}} | " + rep_cells([0, k, w]))
    if not top:
        out.append("(no matches with kills logged yet)")
    out.append("=" * len(BEST_HEAD))
    return "\n".join(out) + "\n"


def m_text(d):
    """This month's kills and wins, then the all-time highest-kill matches."""
    cur, _, m = load_current(d)
    t = log_agg(m.logs)
    return (f"MONTH {cur}  |  " + paint(f"KILLS {t[1]:,}  |  WINS {t[2]:,}") + "\n\n" +
            best_matches(top_matches(m.top, m.logs)))


def lv_text(d):
    _, _, m = load_current(d)
    return lv_report(m.logs, m.lv)


MLOG_HEAD = f"{'DATE':<16} | {'LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)


def match_log(month, logs):
    """'log': every match entry of the current file, oldest first. Entries logged by an
    account or base update (SRC A / B) and level-only updates (SRC L) are left out."""
    dash = "-" * len(MLOG_HEAD)
    out = [f"# MATCH LOG  (month {month}; account and base updates excluded)", paint(MLOG_HEAD), dash]
    rows = [e for e in logs if e.src == SRC_MATCH]
    for e in rows:
        out.append(f"{e.date:<16} | {e.legend:<{LEG_W}} | " + rep_cells([0, e.kills, e.wins]))
    if not rows:
        out.append("(no matches logged this month)")
    out.append("=" * len(MLOG_HEAD))
    return "\n".join(out) + "\n"


LLOG_HEAD = f"{'DATE':<16} | {'LEVEL':>7} | {'CHANGE':>7}"


def level_log(month, logs, lv):
    """'logl': every recorded level, oldest first: the carried @LV days of earlier months (last
    level per day) and each current-month entry with a level, with the change from the row before."""
    dash = "-" * len(LLOG_HEAD)
    out = [f"# LEVEL HISTORY  (month {month}; earlier months: last level per day)", LLOG_HEAD, dash]
    prev = None
    for when, n in list(lv) + [(e.date, e.level) for e in logs if e.level]:
        change = f"{n - prev:+,}" if prev is not None else "-"
        out.append(f"{when:<16} | " + orange(num(n, 7)) + " | " + orange(f"{change:>7}"))
        prev = n
    if prev is None:
        out.append("(no level recorded yet)")
    out.append("=" * len(LLOG_HEAD))
    return "\n".join(out) + "\n"


def log_text(d):
    cur, _, m = load_current(d)
    return match_log(cur, m.logs)


def logl_text(d):
    cur, _, m = load_current(d)
    return level_log(cur, m.logs, m.lv)


VIEWS = {"report": report_text, "l": legend_text, "k": kills_text, "w": wins_text,
         "m": m_text, "lv": lv_text, "log": log_text, "logl": logl_text,
         "lw": lambda d: legend_text(d, "w"), "la": lambda d: legend_text(d, "a"), "lm": lambda d: legend_text(d, "m")}
