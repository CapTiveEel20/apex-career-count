"""Read-only views: report, l / lw / la / lm / ls <name>, k, w, g, log (each reads the current
file once)."""
from datetime import date, datetime, timedelta
from operator import attrgetter

from apex.config import DAY_FMT, LEG_W, NO_LEGEND, REF_W, REP, SRC_MATCH, TOP_GAMES, TOP_MONTH_BESTS
from apex.core.aggregates import last_logged, legend_agg, legend_periods, log_agg, monthly_bests, top_matches
from apex.core.levels import first_level, level_name, level_short
from apex.core.records import LevelDay
from apex.display.colors import green, orange, paint, red
from apex.display.messages import account_line
from apex.display.tables import LREP_HEAD, REP_NAMES, num, rep_cells, side_by_side, vals_cells
from apex.storage.account_file import load_acct, load_account
from apex.storage.monthly_file import load_current, older_logs

WINDOWS = (("1 WEEK", 7), ("1 MONTH", 30), ("3 MONTHS", 90), ("6 MONTHS", 180), ("1 YEAR", 365))  # days
TOP_N = 3
TOP_HEAD = f"{'#':<2} | {'LEGEND':<{LEG_W}} | {'KILLS':>8}"
LAST_HEAD = LREP_HEAD + f" | {'LAST MATCH':<16}"
# 'l' left-column orders: (key(row, last), highest first?). k = all-time kills, w = all-time wins,
# a = by name, m = last match (most recent first; never played = "" = at the bottom). Ties keep name order.
L_SORTS = {"k": (lambda row, last: row.periods.alltime.kills, True),
           "w": (lambda row, last: row.periods.alltime.wins, True),
           "a": (lambda row, last: row.legend.lower(), False),
           "m": (lambda row, last: last.get(row.legend, ""), True)}


def top_legends(logs, n=TOP_N):
    """The n legends with the most kills logged in this file: [(legend, Tally)].
    Ties: more wins first, then by name. Legends with no kills this month are left out."""
    agg = legend_agg(logs)
    names = [leg for leg, t in agg.items() if leg != NO_LEGEND and t.kills > 0]
    names.sort(key=lambda leg: (-agg[leg].kills, -agg[leg].wins, leg))
    return [(leg, agg[leg]) for leg in names[:n]]


def legend_report(month, logs, hl, pl, bases, ll=None, sort="k", search=None):
    """'l': two tables side by side. Left: every legend set with 'base' and its all-time totals
    (base + logged entries), kills and wins only, no grand total, with the date and time of its
    last logged match (ll = carried @LL values; '-' = none yet). sort = a key of L_SORTS (ties keep
    name order); search = only the legends whose name contains it (any case).
    Right: the TOP_N legends by kills logged in the current month (never filtered)."""
    dash = "-" * len(LAST_HEAD)
    left = ["# ALL-TIME BY LEGEND  (base + logged)", paint(LAST_HEAD), dash]
    rows = [row for row in legend_periods(month, logs, hl, pl, bases) if row.legend in bases]
    if search:
        rows = [row for row in rows if search.lower() in row.legend.lower()]
    last = last_logged(ll or {}, logs)
    key, desc = L_SORTS[sort]
    rows.sort(key=lambda row: key(row, last), reverse=desc)  # stable, also when reversed
    for leg, ps in rows:
        left.append(f"{leg:<{LEG_W}} | " + rep_cells(ps.alltime) + f" | {last.get(leg, '-')}")
    if not rows:
        left.append(f"(no base legend matches '{search[:LEG_W]}')" if search and bases else "(no base legends yet)")
    left.append("=" * len(LAST_HEAD))
    tdash = "-" * len(TOP_HEAD)
    right = [f"# TOP {TOP_N} THIS MONTH  ({month})", paint(TOP_HEAD), tdash]
    top = top_legends(logs)
    for i, (leg, t) in enumerate(top, 1):
        right.append(f"{i:<2} | {leg:<{LEG_W}} | " + red(num(t.kills, 8)))
    if not top:
        right.append("(no kills this month)")
    right.append("=" * len(TOP_HEAD))
    return "\n".join(side_by_side(left, right, gap=3)) + "\n"  # gap 3 keeps the report compact (85 columns)


STAT_COLS = (("MONTH", 8), ("SEMIANNUAL", 10), ("ANNUAL", 8), ("ALL-TIME", 8))
STAT_HEAD = f"{'# LEGEND':<{LEG_W}} | " + vals_cells([n for n, _ in STAT_COLS], STAT_COLS)


def stat_report(month, logs, hl, pl, stat, bases=None):
    """One stat ('kills' or 'wins') per legend: monthly, semiannual, annual, all-time
    (all-time includes the legend's base)."""
    dash = "-" * len(STAT_HEAD)
    fn = red if stat == "kills" else green  # kills red, wins green
    value = attrgetter(stat)

    def cells(vals):
        return " | ".join(fn(num(v, w)) for v, (_, w) in zip(vals, STAT_COLS))

    head = f"{'# LEGEND':<{LEG_W}} | " + cells([n for n, _ in STAT_COLS])
    out = [paint(f"# {stat.upper()} BY LEGEND") + f"  (current month: {month})", head, dash]
    rows = legend_periods(month, logs, hl, pl, bases)
    total = [0] * len(STAT_COLS)
    for leg, ps in rows:
        vals = [value(t) for t in ps]
        total = [a + b for a, b in zip(total, vals)]
        out.append(f"{leg:<{LEG_W}} | " + cells(vals))
    if rows:  # combined across all legends; ALL-TIME = absolute historical total
        out += [dash, f"{'GRAND TOTAL':<{LEG_W}} | " + cells(total)]
    else:
        out.append("(no legends recorded yet)")
    out.append("=" * len(STAT_HEAD))
    return "\n".join(out) + "\n"


def _from_day(today, days):
    return (today - timedelta(days=days)).strftime(DAY_FMT)


def period_summary(today, logs, alltime):
    """Left table of 'report' (lines): kills and wins over the same windows as levels_gained (entries
    after FROM, up to today), then the all-time totals. logs must reach back to the longest window."""
    end = today.strftime(DAY_FMT)
    head = f"{'PERIOD':<{REF_W}} | {'FROM':<10} | " + vals_cells(REP_NAMES, REP)
    out = [f"# SUMMARY  (today: {end})", paint(head), "-" * len(head)]
    for label, days in WINDOWS:
        s = _from_day(today, days)
        out.append(f"{label:<{REF_W}} | {s:<10} | " + rep_cells(log_agg([e for e in logs if s < e.date[:10] <= end])))
    out += [f"{'ALL-TIME':<{REF_W}} | {'-':<10} | " + rep_cells(alltime), "=" * len(head)]
    return out


def levels_gained(logs, lv, first):
    """Right table of 'report' (lines): levels gained over each window, then since first (the first
    level ever recorded; 0 if none)."""
    today = date.today()
    end = today.strftime(DAY_FMT)
    # (day or timestamp, level): carried days + every current-month entry, so gains within a
    # single day are counted too. Sorted by time only: same-minute entries stay in ID order.
    points = sorted((x for x in lv + [LevelDay(e.date, e.level) for e in logs if e.level] if x.day[:10] <= end),
                    key=lambda x: x.day)
    current = points[-1].level if points else 0
    head = f"{'PERIOD':<{REF_W}} | {'FROM':<10} | "
    width = len(head) + 7
    out = [f"# LEVELS GAINED  (today: {end}, " + orange(f"current: {level_name(current)}") + ")",
           head + " " + orange("GAINED"), "-" * width]
    for label, days in WINDOWS:
        s = _from_day(today, days)
        base = [n for k, n in points if k[:10] <= s]
        inside = [n for k, n in points if k[:10] > s]
        gained = current - (base[-1] if base else inside[0]) if points and (base or inside) else 0
        out.append(f"{label:<{REF_W}} | {s:<10} | " + orange(num(gained, 7)))
    out += [f"{'ALL-TIME':<{REF_W}} | {'-':<10} | " + orange(num(current - first if points else 0, 7)), "=" * width]
    return out


def report_text(d):
    """Kills and wins per period next to the levels gained, over the same windows. The current file is
    read once; the older months are read for the windows and the first level."""
    cur, path, m = load_current(d)
    logs = older_logs(d, cur) + m.logs
    left = period_summary(date.today(), logs, m.hist + log_agg(m.logs))
    tables = side_by_side(left, levels_gained(m.logs, m.lv, first_level(logs, m.lv)), gap=3)
    return f"File: {path}\n\n" + account_line(load_account(d)) + "\n" + "\n".join(tables) + "\n"


def legend_text(d, sort="k", search=None):
    """'l' (by kills), 'lw' (by wins), 'la' (by name), 'lm' (by last match); 'ls <name>' = search
    (by kills). sort = a key of L_SORTS."""
    cur, path, m = load_current(d)
    return (f"File: {path}\n\n" +
            legend_report(cur, m.logs, m.hl, m.pl, load_acct(d).bases, m.ll, sort, search))


def kills_text(d):
    cur, _, m = load_current(d)
    data = load_acct(d)
    return account_line(data.account, "kills") + "\n" + stat_report(cur, m.logs, m.hl, m.pl, "kills", data.bases)


def wins_text(d):
    cur, _, m = load_current(d)
    data = load_acct(d)
    return account_line(data.account, "wins") + "\n" + stat_report(cur, m.logs, m.hl, m.pl, "wins", data.bases)


def win_cell(r):
    """WIN column of 'g' and 'log': W (green) if the match had a win, else L (red)."""
    return green(f"{'W':<3}") if r.wins > 0 else red(f"{'L':<3}")


def game_table(title, when_head, when_w, rows, when, empty):
    """One table of 'g' (lines): rank, kills, win (W = the match had a win, else L), legend, then
    when(row) in a column when_w wide."""
    head = f"{'#':<2} | {'KILLS':>6} | {'WIN':<3} | {'LEGEND':<{LEG_W}} | {when_head:<{when_w}}"
    out = [title, paint(head), "-" * len(head)]
    for i, r in enumerate(rows, 1):
        out.append(f"{i:<2} | " + red(num(r.kills, 6)) + f" | {win_cell(r)} | {r.legend:<{LEG_W}} | {when(r):<{when_w}}")
    return out + ([] if rows else [empty]) + ["=" * len(head)]


def month_year(r):
    """Month and year of a match: Nov 2026."""
    return datetime.strptime(r.date[:7], "%Y-%m").strftime("%b %Y")


def games_text(d):
    """'g': the month's best games next to the all-time monthly bests. If the newest file is from an
    earlier month, that month is already over: it counts as closed here too, before the first record
    of the new month rolls it over."""
    cur, _, m = load_current(d)
    month = date.today().strftime("%Y-%m")
    closed = month > cur
    games = top_matches([], [] if closed else m.logs, TOP_GAMES)
    bests = monthly_bests(m.bests, m.logs) if closed else m.bests
    left = game_table(f"# TOP {TOP_GAMES} GAMES THIS MONTH  ({month if closed else cur})", "DATE", 10, games,
                      lambda r: r.date[:10], "(no matches with kills this month)")
    right = game_table(f"# ALL-TIME TOP {TOP_MONTH_BESTS} MONTHLY BESTS", "MONTH", 8, bests, month_year,
                       "(no closed months yet)")
    return "\n".join(side_by_side(left, right, gap=3)) + "\n"


LOG_RECENT = 20  # rows of each 'log' table
# 'log' column widths: the two tables and their gap fit in 79 columns
MLOG_HEAD = f"{'DATE':<16} | {'LEGEND':<{LEG_W}} | {'KILLS':>6} | {'WIN':<3}"
LLOG_HEAD = f"{'DATE':<10} | {'LEVEL':>6} | {'CHANGE':>6}"


def match_log(month, logs):
    """Left table of 'log' (lines): the last LOG_RECENT match entries of the current file, oldest
    first. Entries logged by an account or base update (SRC A / B) and level-only updates (SRC L)
    are left out."""
    dash = "-" * len(MLOG_HEAD)
    out = [f"# MATCHES  ({month}, last {LOG_RECENT})", paint(MLOG_HEAD), dash]
    rows = [e for e in logs if e.src == SRC_MATCH][-LOG_RECENT:]
    for e in rows:
        out.append(f"{e.date:<16} | {e.legend:<{LEG_W}} | " + red(num(e.kills, 6)) + " | " + win_cell(e))
    if not rows:
        out.append("(no matches logged this month)")
    out.append("=" * len(MLOG_HEAD))
    return out


def level_log(logs, lv):
    """Right table of 'log' (lines): the last LOG_RECENT recorded levels, oldest first: the carried
    @LV days of earlier months and each current-month entry with a level, with the change from
    the level before."""
    rows, prev = [], None
    for when, n in list(lv) + [(e.date, e.level) for e in logs if e.level]:
        change = f"{n - prev:+,}" if prev is not None else "-"
        rows.append(f"{when[:10]:<10} | " + orange(f"{level_short(n):>6}") + " | " + orange(f"{change:>6}"))
        prev = n
    dash = "-" * len(LLOG_HEAD)
    return ([f"# LEVELS  (last {LOG_RECENT})", LLOG_HEAD, dash] + (rows[-LOG_RECENT:] or ["(no level recorded yet)"]) +
            ["=" * len(LLOG_HEAD)])


def log_text(d):
    """'log': recent matches on the left, recent levels on the right."""
    cur, _, m = load_current(d)
    return "\n".join(side_by_side(match_log(cur, m.logs), level_log(m.logs, m.lv), gap=3)) + "\n"


VIEWS = {"report": report_text, "l": legend_text, "k": kills_text, "w": wins_text,
         "g": games_text, "log": log_text,
         "lw": lambda d: legend_text(d, "w"), "la": lambda d: legend_text(d, "a"), "lm": lambda d: legend_text(d, "m")}
