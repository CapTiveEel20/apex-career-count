#!/usr/bin/env python3
"""Apex Legends stats tracker on plain .txt files (standard library only).

Usage:
  python apex_stats.py add <kills> <wins> [legend] [level] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
  python apex_stats.py report
  python apex_stats.py l        (all-time kills and wins per legend: base + logged entries)
  python apex_stats.py m
  python apex_stats.py <n> | <n>l | +<n>  [--date ...]   (set level n / add n levels)
  python apex_stats.py <n>k | <n>w        [--date ...]   (n kills only / n wins only, no legend)
  python apex_stats.py lv       (level report)
  python apex_stats.py k | w    (kills / wins per legend)
  python apex_stats.py undo
  python apex_stats.py account [<kills> <wins> [legend] [level]] [--l NAME] [--date ...]
                                (show the global all-time account totals; the first time, save them;
                                 afterwards, log the gain (new - saved) as a match entry)
  python apex_stats.py base [<legend> <kills> <wins>] [--date ...]
                                (list the bases; the first time, set a legend's all-time totals;
                                 afterwards, log the gain (new - current) as a match for it)
  python apex_stats.py c        (quick-start cheat sheet)
  python apex_stats.py          (interactive mode: "<kills> <wins> [legend] [level]", <n>, <n>l,
                                 <n>k, <n>w, account [kills] [wins], base <legend> <kills> <wins>,
                                 report, l, k, w, m, lv, undo, c, date YYYY-MM-DD | date today;
                                 an empty line quits)
  Sticky legend (interactive mode): a typed legend is remembered and reused by later matches and
  account entries that omit it; typing another legend replaces it ("-" clears it). <n>k / <n>w
  never use it.
  Every match adds its kills/wins to its legend's all-time totals (base + logged) and to the
  global account totals.
  Terminal numbers use thousands separators (15,000); kills/wins input may use them too.
  Global option: --dir <folder>  (default: ./apex_data next to the script)

Smart parsing of [legend] [level]: if the 3rd value is a number it is the level (no legend),
otherwise it is the legend and a trailing number is the level.
Every level value, in full entries and level-only input alike: "700" = absolute level (rejected if
lower than the last recorded level), "+3" = last recorded level + 3.

"level" is the account level reached (0 = not recorded). It can never go down: a new level
must be >= the last level recorded before its date and <= the next level recorded after it.
"+<n>" records (last level recorded before the entry's date) + n.

Rotation by calendar month: one file per month (apex_stats_YYYY-MM.txt).
Global account totals (set with "account <kills> <wins>") and the per-legend bases (set with
"base <legend> <kills> <wins>") live in their own file, account_stats.txt, so they survive every
rotation; report, k and w show the account totals on top. Once set, every saved match adds its
kills/wins to them and undo subtracts them again.

Terminal output is colorized with raw ANSI codes (kills red, wins green) when stdout is a
terminal and NO_COLOR is not set. Data files never contain color codes.

File format (O(1) parsing per line via a constant prefix in the first column):
  @FILE  month of the file    @HIST  all-time totals of previous months
  @PREV  per-month totals (last 11 calendar months, for semiannual/annual)
  @HL    all-time totals per legend (previous months)
  @PL    per-month, per-legend totals (last 11 months)
  @LV    highest level reached per day (previous months, last year + 1 baseline)
  L      one log entry (date, legend, kills, wins, level, id)
  #      headers/comments (ignored by the parser)
  Summaries after "# SUMMARY" are recomputed on every write and never parsed.
"""
import argparse
import calendar
import os
import re
import sys
from datetime import date, datetime, timedelta

SEMI_MONTHS = 6
YEAR_MONTHS = 12
LV_KEEP_DAYS = 366
FNAME = "apex_stats_{}.txt"
FRE = re.compile(r"^apex_stats_(\d{4}-\d{2})\.txt$")
NUM_RE = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)$")  # kills/wins: "15000" or "15,000"
QUICK_RE = re.compile(r"^\+?(\d+)([kwl])$", re.IGNORECASE)  # quick-add: "5k" kills only, "1w" wins only, "3l" +3 levels
LEVEL_RE = re.compile(r"^\+?\d+$")  # level-only input: "700" (absolute) or "+5" (relative)
LVL_TOKEN_RE = re.compile(r"^[+-]?\d+$")  # [level] in a full entry: "700", "+5" (relative) or "-5" (rejected)
FOOTER_MARK = "# SUMMARY"
NO_LEGEND = "-"
DFMT = "%Y-%m-%d %H:%M"
DAY_FMT = "%Y-%m-%d"
ACCOUNT_FILE = "account_stats.txt"  # global all-time account totals (never rotated)
ACC_TAG = "@ACCOUNT"
BASE_TAG = "@BASE"  # per-legend base: all-time totals minus the logged entries (same file)

# Raw ANSI colors (no external libraries): kills red, wins green. Enabled by init_color().
RED, GREEN, RESET = "\033[91m", "\033[92m", "\033[0m"
COLOR = False
KW_RE = re.compile(r"[<\[]?\b(?:(kills?)|(wins?))\b[>\]]?(?:\s+\d(?:[\d,]*\d)?)?", re.IGNORECASE)


def num(v, w=0, sep=True):
    """Right-aligned number with thousands separators (15,000) for the terminal; sep=False
    (data files) keeps plain digits. Non-numbers (table headers) are just aligned."""
    return f"{v:>{w},}" if sep and isinstance(v, int) else f"{v:>{w}}"


def to_int(s):
    """Whole number from user input, with or without thousands separators ("15,000")."""
    return int(s.replace(",", ""))


def init_color():
    """Colors only on a real terminal, unless NO_COLOR is set. On Windows, turn on the
    console's ANSI (virtual terminal) mode with ctypes from the standard library."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            if not k32.GetConsoleMode(h, ctypes.byref(mode)):
                return False
            k32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        except (AttributeError, OSError):
            return False
    return True


def _on(color):
    return COLOR if color is None else color


def red(s, color=None):
    return f"{RED}{s}{RESET}" if _on(color) else str(s)


def green(s, color=None):
    return f"{GREEN}{s}{RESET}" if _on(color) else str(s)


def paint(text, color=None):
    """Color kill words (kills, <kills>, KILLS 12) red and win words (wins, [wins], WINS 3) green.
    Used for prose and table headers; table values are colored cell by cell."""
    if not _on(color):
        return text
    return KW_RE.sub(lambda m: red(m.group(0), True) if m.group(1) else green(m.group(0), True), text)

# Aggregates: LOGS, KILLS, WINS
AGG = (("LOGS", 6), ("KILLS", 8), ("WINS", 8))  # stored in header lines (LOGS kept for file-format compatibility)
REP = AGG[1:]  # columns shown in report tables: KILLS, WINS (no LOGS)
NA = len(AGG)
TAG_W, REF_W, LEG_W = 7, 13, 12
# Log record: (date, legend, kills, wins, level, id, acc)  acc = 1 if added to the account totals


def zero():
    return [0] * NA


def vadd(a, b):
    return [x + y for x, y in zip(a, b)]


def ints(cells):
    return [int(x) for x in cells[:NA]]


def midx(month):
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def months_ago(d, n):
    y, m = divmod(d.year * 12 + d.month - 1 - n, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def log_agg(logs):
    t = zero()
    for r in logs:
        t[0] += 1; t[1] += r[2]; t[2] += r[3]
    return t


def legend_agg(logs):
    d = {}
    for r in logs:
        t = d.setdefault(r[1], zero())
        t[0] += 1; t[1] += r[2]; t[2] += r[3]
    return d


def day_levels(logs):
    """day -> highest level recorded that day (level 0 = not recorded)."""
    d = {}
    for r in logs:
        if r[4]:
            day = r[0][:10]
            d[day] = max(d.get(day, 0), r[4])
    return d


def periods(month, cur, hist, prev):
    """(monthly, semiannual, annual, all-time); prev = [(month, values)]."""
    ci = midx(month)
    semi = year = cur
    for m, v in prev:
        d = ci - midx(m)
        if d < SEMI_MONTHS:
            semi = vadd(semi, v)
        if d < YEAR_MONTHS:
            year = vadd(year, v)
    return cur, semi, year, vadd(hist, cur)


def vals_cells(vals, cols=AGG):
    return " | ".join(f"{v:>{w}}" for v, (_, w) in zip(vals, cols))


def row(tag, ref, vals):
    return f"{tag:<{TAG_W}} | {ref:<{REF_W}} | " + vals_cells(vals)


def rep_cells(t, color=None, sep=True):
    """Report columns only (KILLS red, WINS green): the stored LOGS count is never shown."""
    (_, kw), (_, ww) = REP
    return f"{red(num(t[1], kw, sep), color)} | {green(num(t[2], ww, sep), color)}"


def sum_row(label, t, color=None, sep=True):
    return f"{label:<{REF_W}} | " + rep_cells(t, color, sep)


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
REP_NAMES = [n for n, _ in REP]
SUM_HEAD = f"{'REFERENCE':<{REF_W}} | " + vals_cells(REP_NAMES, REP)
W = max(len(SUM_HEAD), len(AGG_HEAD), len(PL_HEAD), len(LOG_HEAD))
LREP_HEAD = f"{'# LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)
PERIOD_LABELS = ("MONTH {}", "SEMIANNUAL", "ANNUAL", "ALL-TIME")


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


def summary(month, hist, prev, logs, color=None, sep=True):
    out = [f"{FOOTER_MARK}  (updated: {datetime.now():{DFMT}})", paint(SUM_HEAD, color), "-" * len(SUM_HEAD)]
    for lbl, t in zip(PERIOD_LABELS, periods(month, log_agg(logs), hist, prev)):
        out.append(sum_row(lbl.format(month), t, color, sep))
    out.append("=" * len(SUM_HEAD))
    return "\n".join(out) + "\n"


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


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def clean(s, w):
    s = (s or "").replace("|", "/").strip().capitalize()[:w]
    return s or NO_LEGEND


def level_arg(token):
    """Level token -> (level, delta): "700" = absolute (700, None); "+3" = relative (0, 3)."""
    if token.startswith("+"):
        return 0, int(token)
    return int(token), None


def parse_extra(tokens):
    """[legend] [level] -> (legend, level, delta). A numeric 3rd value ("700" or "+3") is the level;
    otherwise it is the legend, and a trailing numeric value is the level. No "+" = absolute level,
    "+<n>" = last recorded level + n."""
    if not tokens:
        return None, 0, None
    if LVL_TOKEN_RE.match(tokens[0]):
        if len(tokens) > 1:
            raise ValueError("Error: nothing may follow the level.")
        return (None,) + level_arg(tokens[0])
    if len(tokens) > 1 and LVL_TOKEN_RE.match(tokens[-1]):
        return (" ".join(tokens[:-1]),) + level_arg(tokens[-1])
    return " ".join(tokens), 0, None


def parse_when(when):
    """None -> now; 'YYYY-MM-DD HH:MM' exact; 'YYYY-MM-DD' -> that day at the current time."""
    if not when:
        return datetime.now()
    when = when.strip()
    for fmt in (DFMT, DAY_FMT):
        try:
            dt = datetime.strptime(when, fmt)
        except ValueError:
            continue
        if fmt == DAY_FMT:
            now = datetime.now()
            dt = dt.replace(hour=now.hour, minute=now.minute)
        return dt
    raise ValueError("Error: date must be 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'.")


def last_level(stamp, logs, lv):
    """Last (= highest) level recorded at or before stamp; 0 if none."""
    before = [n for _, n in lv] + [r[4] for r in logs if r[4] and r[0] <= stamp]
    return max(before, default=0)


def check_level(level, stamp, logs, lv):
    """A level may never go down over time (0 = not recorded, always accepted)."""
    if not level:
        return
    last = last_level(stamp, logs, lv)
    if level < last:
        raise ValueError(f"Error: level {level:,} is lower than the last recorded level ({last:,}).")
    after = [(r[4], r[0]) for r in logs if r[4] and r[0] > stamp]
    if after:
        nxt, when = min(after)
        if level > nxt:
            raise ValueError(f"Error: level {level:,} is higher than level {nxt:,} recorded later ({when}).")


def prune_lv(lv, cutoff):
    """Keep days after cutoff plus the latest earlier day as the baseline for the 1-year window."""
    old = [x for x in lv if x[0] <= cutoff]
    return old[-1:] + [x for x in lv if x[0] > cutoff]


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


def account_path(d):
    return os.path.join(d, ACCOUNT_FILE)


def load_acct(d):
    """(account, bases) from account_stats.txt (one small read).
    account = (kills, wins, updated) or None if never set; bases = {legend: (kills, wins, updated)}."""
    acc, bases = None, {}
    try:
        with open(account_path(d), encoding="utf-8") as f:
            for line in f:
                c = line.split("|")
                tag = c[0].strip()
                try:
                    if tag == ACC_TAG and len(c) >= 3:
                        acc = int(c[1]), int(c[2]), c[3].strip() if len(c) > 3 else ""
                    elif tag == BASE_TAG and len(c) >= 4:
                        bases[c[1].strip()] = int(c[2]), int(c[3]), c[4].strip() if len(c) > 4 else ""
                except ValueError:
                    continue  # damaged line: skip it, keep the rest
    except OSError:
        pass
    return acc, bases


def load_account(d):
    """(kills, wins, updated) of the global account totals, or None if never set."""
    return load_acct(d)[0]


def write_acct(d, acc, bases):
    """Write account_stats.txt (1 atomic write): the @ACCOUNT line (if set) and the @BASE lines."""
    os.makedirs(d, exist_ok=True)
    head = f"{'# TAG':<9} | {'KILLS':>10} | {'WINS':>10} | UPDATED"
    bhead = f"{'# TAG':<9} | {'LEGEND':<{LEG_W}} | {'KILLS':>10} | {'WINS':>10} | UPDATED"
    eq = "=" * (len(bhead) + 12)
    out = [eq, "  APEX LEGENDS - ACCOUNT TOTALS (global, all-time) AND LEGEND BASES",
           "  Set with: account <kills> <wins>   |   base <legend> <kills> <wins>", eq, head, "-" * len(eq)]
    if acc:
        out.append(f"{ACC_TAG:<9} | {acc[0]:>10} | {acc[1]:>10} | {acc[2]}")
    out += ["", "# @BASE = per-legend all-time totals not covered by logged entries (set with base)", bhead, "-" * len(eq)]
    out += [f"{BASE_TAG:<9} | {leg:<{LEG_W}} | {k:>10} | {w:>10} | {upd}"
            for leg, (k, w, upd) in sorted(bases.items())]
    write_atomic(account_path(d), "\n".join(out) + "\n")


def save_account(d, kills, wins):
    """Write the global all-time account totals, keeping the legend bases (1 atomic write)."""
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    stamp = f"{datetime.now():{DFMT}}"
    write_acct(d, (kills, wins, stamp), load_acct(d)[1])
    return kills, wins, stamp


def bump_account(d, kills, wins):
    """Add (or, with negative values, subtract) kills/wins to the saved global account totals.
    No-op when nothing changes or when the totals were never set; never below 0. Used by undo
    for entries flagged acc = 1 (save_log adds directly, after flagging the new entry)."""
    if not (kills or wins):
        return None
    acc = load_account(d)
    if acc is None:
        return None
    return save_account(d, max(0, acc[0] + kills), max(0, acc[1] + wins))


def account_line(acc, which="both"):
    """One display line with the global account totals: which = 'kills', 'wins' or 'both'."""
    if not acc:
        return paint("ACCOUNT  not set yet (use: account <kills> <wins>)") + "\n"
    k, w, upd = acc
    vals = {"kills": [f"KILLS {k:,}"], "wins": [f"WINS {w:,}"], "both": [f"KILLS {k:,}", f"WINS {w:,}"]}[which]
    note = f"  (global, all-time; updated {upd})" if upd else "  (global, all-time)"
    return paint("ACCOUNT  " + "  |  ".join(vals)) + note + "\n"


def account_cmd(d, args, when=None, default_legend=None, legend=None):
    """'account' shows the totals. 'account <kills> <wins> [legend] [level]':
    - first time (no totals yet): saves the totals, nothing is logged;
    - afterwards: logs the gain (new - saved) as one match entry through save_log, which then moves
      the totals to the new values (undo takes it back out);
    - new totals lower than the saved ones: a correction, the totals are replaced, nothing logged.
    default_legend = sticky legend (REPL); legend = --l (CLI). Returns (text, rec or None, typed legend)."""
    if not args:
        return account_line(load_account(d)), None, None
    if len(args) < 2 or not (NUM_RE.match(args[0]) and NUM_RE.match(args[1])):
        raise InputError()
    kills, wins = to_int(args[0]), to_int(args[1])
    try:
        typed, level, delta = parse_extra(args[2:])
    except ValueError:
        raise InputError() from None
    if legend:
        typed = legend
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    extra = bool(args[2:] or legend)
    acc = load_account(d)
    if acc is None:  # first time: just store the starting totals
        if extra:
            raise ValueError("Error: the first 'account <kills> <wins>' only saves your totals (no legend or level).")
        return "SAVED - " + account_line(save_account(d, kills, wins)), None, None
    dk, dw = kills - acc[0], wins - acc[1]
    if dk < 0 or dw < 0:  # lower than before: a correction, nothing to log
        if extra:
            raise ValueError("Error: these totals are lower than the saved ones (" +
                             paint(f"KILLS {acc[0]:,} | WINS {acc[1]:,}") +
                             "); a correction only replaces the totals (no legend or level).")
        return ("SAVED - " + account_line(save_account(d, kills, wins)).rstrip("\n") +
                "\n  (lower than the saved totals: corrected, nothing logged)\n"), None, None
    if not (dk or dw or level or delta):
        return ("ACCOUNT  already up to date: " + paint(f"KILLS {acc[0]:,}  |  WINS {acc[1]:,}") +
                ", nothing logged.\n"), None, None
    leg = typed if typed is not None else default_legend
    _, _, _, rec = save_log(d, dk, dw, leg, when, level, delta, account=acc)
    line = ("ACCOUNT  " + red(f"KILLS {acc[0]:,} -> {kills:,} (+{dk:,})") + "  |  " +
            green(f"WINS {acc[1]:,} -> {wins:,} (+{dw:,})") + "\n")
    return line + fmt_saved(rec) + "\n", rec, typed


def save_base(d, legend, kills, wins, acct=None):
    """Store (or, with 0 0, remove) a legend's base, keeping the account totals.
    acct = (account, bases) already loaded by the caller, so the file is not read twice."""
    acc, bases = acct or load_acct(d)
    if kills or wins:
        bases[legend] = (kills, wins, f"{datetime.now():{DFMT}}")
    else:
        bases.pop(legend, None)
    write_acct(d, acc, bases)


def legend_logged(d):
    """{legend: [logs, kills, wins]} of every logged entry, all-time (@HL + the current file; 1 read)."""
    cur = current_month(d)
    if not cur:
        return {}
    _, _, logs, hl, _, _ = load(os.path.join(d, FNAME.format(cur)))
    out = {leg: list(t) for leg, t in hl.items()}
    for leg, t in legend_agg(logs).items():
        out[leg] = vadd(out.get(leg, zero()), t)
    return out


def base_table(bases, logged):
    """'base': every legend with a base and its all-time totals (base + logged entries)."""
    head = f"{'# LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)
    dash = "-" * len(head)
    out = ["# LEGEND BASES  (all-time totals per legend: base + logged entries)", paint(head), dash]
    for leg, (k, w, _) in sorted(bases.items()):
        t = logged.get(leg, zero())
        out.append(f"{leg:<{LEG_W}} | " + rep_cells([0, k + t[1], w + t[2]]))
    if not bases:
        out.append("(no bases set yet; use: base <legend> <kills> <wins>)")
    out.append("=" * len(head))
    return "\n".join(out) + "\n"


def base_cmd(d, args, when=None):
    """'base' lists the legend bases. 'base <legend> <kills> <wins>' = the legend's all-time totals:
    - legend not listed yet: they become its all-time totals (the entries already logged for it are
      included, nothing is added on top): the base stores only the part not covered by logged
      entries, and nothing is logged, so the account totals don't change;
    - legend already listed: like 'account', the gain (new - current all-time totals) is logged as
      a match for that legend through save_log (so it reaches the account totals too; undo takes
      it back); lower values are a correction of the base, nothing logged;
    - 0 0 removes the base."""
    acct = load_acct(d)
    if not args:
        return base_table(acct[1], legend_logged(d))
    if len(args) < 3 or not (NUM_RE.match(args[-2]) and NUM_RE.match(args[-1])):
        raise InputError()
    legend = clean(" ".join(args[:-2]), LEG_W)
    if legend == NO_LEGEND or LVL_TOKEN_RE.match(legend):
        raise InputError()
    kills, wins = to_int(args[-2]), to_int(args[-1])
    if kills < 0 or wins < 0:
        raise ValueError("Error: base kills and wins cannot be negative.")
    bases = acct[1]
    if not (kills or wins):
        if legend not in bases:
            raise ValueError(f"Error: {legend} has no base to remove.")
        save_base(d, legend, 0, 0, acct)
        return f"REMOVED - BASE {legend}\n"
    t = legend_logged(d).get(legend, zero())
    lk, lw = t[1], t[2]  # kills / wins already logged for this legend
    saved = ("SAVED - BASE  " + f"{legend}  " + paint(f"KILLS {kills:,}  |  WINS {wins:,}") +
             "  (all-time totals of this legend)\n")
    if kills < lk or wins < lw:
        raise ValueError(f"Error: {legend} already has " + paint(f"KILLS {lk:,} | WINS {lw:,}") +
                         " in logged entries; its all-time totals can't be lower.")
    if legend not in bases:  # first time: set the all-time totals, nothing logged
        save_base(d, legend, kills - lk, wins - lw, acct)
        return saved
    bk, bw = bases[legend][:2]
    tk, tw = bk + lk, bw + lw  # current all-time totals
    dk, dw = kills - tk, wins - tw
    if dk < 0 or dw < 0:  # lower than before: correct the base, nothing logged
        save_base(d, legend, kills - lk, wins - lw, acct)
        return saved.rstrip("\n") + "\n  (lower than the saved totals: corrected, nothing logged)\n"
    if not (dk or dw):
        return (f"BASE  {legend}  already up to date: " + paint(f"KILLS {tk:,}  |  WINS {tw:,}") +
                ", nothing logged.\n")
    _, _, _, rec = save_log(d, dk, dw, legend, when, account=acct[0])
    line = (f"BASE  {legend}  " + red(f"KILLS {tk:,} -> {kills:,} (+{dk:,})") + "  |  " +
            green(f"WINS {tw:,} -> {wins:,} (+{dw:,})") + "\n")
    return line + fmt_saved(rec) + "\n"


def logs_word(n):
    return f"{n:,} log" + ("" if n == 1 else "s")


def is_level_only(rec):
    return not rec[2] and not rec[3] and rec[4] and rec[1] == NO_LEGEND


def fmt_saved(rec):
    if is_level_only(rec):
        return f"SAVED - LEVEL {rec[4]:,} ({rec[0][:10]})"
    return (f"SAVED  {rec[1]}  " + paint(f"WINS {rec[3]:,}  KILLS {rec[2]:,}") +
            f"  LEVEL {rec[4]:,}  ({rec[0]})")


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


def cmd_add(a):
    try:
        vals = a.values
        if len(vals) < 2:
            raise ValueError("Format: add <kills> <wins> [legend] [level]   "
                             "(a level alone: python apex_stats.py 700  or  +5)")
        if not (NUM_RE.match(vals[0]) and NUM_RE.match(vals[1])):
            raise ValueError("Error: kills and wins must be whole numbers.")
        legend, level, delta = parse_extra(vals[2:])
        if a.legend:
            legend = a.legend
        _, shown, _, rec = save_log(a.dir, to_int(vals[0]), to_int(vals[1]), legend, a.date, level, delta)
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(fmt_saved(rec) + "\n")
    print(shown, end="")


def cmd_level(argv):
    """python apex_stats.py [--dir PATH] <n> | <n>l | +<n> | <n>k | <n>w [--date ...]"""
    lp = argparse.ArgumentParser(prog="apex_stats.py", usage="\n  " + USAGE_NUM)
    lp.add_argument("value", metavar="<n> | <n>l | <n>k | <n>w")
    lp.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"')
    lp.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR)
    a = lp.parse_args(argv)
    try:
        _, _, _, rec = save_quick(a.dir, a.value, a.date)
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(fmt_saved(rec))


def parse_day(s):
    try:
        return datetime.strptime(s, DAY_FMT).strftime(DAY_FMT)
    except ValueError:
        raise ValueError("Error: use 'date YYYY-MM-DD' or 'date today'.") from None


MENU_W = 79
QUICK_GUIDE = (
    "\n===============================================================================\n"
    "                              APEX STATS TRACKER\n"
    "===============================================================================\n"
    " [ SETUP ]   account <kills> <wins> (1st: saves totals; later: logs new - old)\n"
    " [ BASE ]    base <legend> <kills> <wins> (1st: sets total; later: logs gain)\n"
    " [ MATCH ]   <kills> <wins> [legend] [level] (e.g. 5 1 wraith 57 | 5 1 57)\n"
    " [ QUICK ]   <n>k | <n>w (kills only | wins only, no legend; e.g. 5k | 1w)\n"
    " [ LEVEL ]   <n> | <n>l (e.g. 700 sets level 700 | 3l adds 3 levels)\n"
    " [ REPORT ]  report | l | k | w | m | lv\n"
    " [ TOOLS ]   undo | date YYYY-MM-DD | date today | c (help)\n"
    ' [ LEGEND ]  sticky: the last legend typed is reused by matches ("-" clears)\n'
    "-------------------------------------------------------------------------------\n"
    " Press Enter on an empty line to quit.\n"
)
MENU_TITLE = QUICK_GUIDE[:QUICK_GUIDE.index(" [ SETUP ]")]  # shared banner: QUICK_GUIDE and cheat_text
QUICK_TXT_RE = re.compile(r"(?<![\w+<])\+?(?:<n>|\d+)([kw])\b")  # <n>k / 5k (red), <n>w / 1w (green)


def color_quick(text):
    """Quick-add shortcuts (<n>k red, <n>w green) in menu text (paint does not match them)."""
    if not COLOR:
        return text
    return QUICK_TXT_RE.sub(lambda m: red(m.group(0)) if m.group(1) == "k" else green(m.group(0)), text)


def quick_guide():
    """QUICK_GUIDE for the terminal: kill words, the k command and <n>k red; win words, w and <n>w green."""
    return color_quick(paint(QUICK_GUIDE).replace("| k | w |", f"| {red('k')} | {green('w')} |"))


class InputError(ValueError):
    """Unrecognized command or malformed input: the REPL answers with QUICK_GUIDE."""


def interactive(d):
    print(quick_guide(), end="")
    day = None  # None = system date
    sticky = None  # sticky legend: last legend typed, reused by matches and account entries that omit it
    while True:
        tags = [t for t in (day, sticky) if t]
        try:
            line = input(f"[{' | '.join(tags)}]> " if tags else "> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd = line.lower()
        if not cmd:  # only an empty line quits
            break
        parts = line.split()
        head = parts[0].lower()
        try:
            if cmd in VIEWS:
                print(VIEWS[cmd](d), end="")
                continue
            if cmd == "undo":
                print(undo(d), end="")
                continue
            if cmd == "c":
                print(cheat_text(cli=False), end="")
                continue
            if head == "date":
                if len(parts) != 2:
                    raise InputError()
                try:
                    day = None if parts[1].lower() == "today" else parse_day(parts[1])
                except ValueError:
                    raise InputError() from None
                print(f"  Active date: {day or 'today (system)'}")
                continue
            when = f"{day} {datetime.now():%H:%M}" if day else None
            if head == "base":  # list / first time: set a legend's all-time totals / later: log the gain
                print(base_cmd(d, parts[1:], when), end="")
                continue
            if head == "account":  # show / first set / log the gain (new - saved) as a match
                text, rec, typed = account_cmd(d, parts[1:], when, sticky)
                print(text, end="")
                if rec and typed is not None:
                    sticky = rec[1] if rec[1] != NO_LEGEND else None
                continue
            if len(parts) == 1 and (LEVEL_RE.match(parts[0]) or QUICK_RE.match(parts[0])):
                _, _, _, rec = save_quick(d, parts[0], when)  # 700, 3l, +3, 5k, 1w (never a legend)
            else:  # anything else must be a match: <kills> <wins> [legend] [level]
                if len(parts) < 2 or not (NUM_RE.match(parts[0]) and NUM_RE.match(parts[1])):
                    raise InputError()
                try:
                    typed, level, delta = parse_extra(parts[2:])
                except ValueError:
                    raise InputError() from None
                legend = typed if typed is not None else sticky
                _, _, _, rec = save_log(d, to_int(parts[0]), to_int(parts[1]), legend, when, level, delta)
                if typed is not None:  # a typed legend replaces the sticky one ("-" clears it)
                    sticky = rec[1] if rec[1] != NO_LEGEND else None
        except InputError:
            print(quick_guide(), end="")
            continue
        except ValueError as e:
            print(paint(str(e)))
            continue
        print(fmt_saved(rec))


def legend_periods(month, logs, hl, pl, bases=None):
    """[(legend, (monthly, semiannual, annual, all-time))] for real legends only:
    entries without a legend ("-", e.g. level-only updates) are excluded.
    The all-time value includes the legend's base (see 'base')."""
    bases = bases or {}
    la = legend_agg(logs)
    by_leg = {}
    for m, leg, t in pl:
        by_leg.setdefault(leg, []).append((m, t))
    legends = sorted(x for x in set(hl) | set(by_leg) | set(la) | set(bases) if x and x != NO_LEGEND)
    out = []
    for leg in legends:
        mo, semi, year, alltime = periods(month, la.get(leg, zero()), hl.get(leg, zero()), by_leg.get(leg, []))
        b = bases.get(leg)
        if b:
            alltime = vadd(alltime, [0, b[0], b[1]])
        out.append((leg, (mo, semi, year, alltime)))
    return out


def legend_report(month, logs, hl, pl, bases):
    """'l': one all-time table per legend (base + every logged entry), kills and wins only."""
    dash = "-" * len(LREP_HEAD)
    out = [f"# ALL-TIME BY LEGEND  (base + logged entries; current month: {month})", paint(LREP_HEAD), dash]
    rows = legend_periods(month, logs, hl, pl, bases)
    total = zero()
    for leg, ps in rows:
        total = vadd(total, ps[3])
        out.append(f"{leg:<{LEG_W}} | " + rep_cells(ps[3]))
    if rows:
        out += [dash, f"{'GRAND TOTAL':<{LEG_W}} | " + rep_cells(total)]
    else:
        out.append("(no legends recorded yet)")
    out.append("=" * len(LREP_HEAD))
    return "\n".join(out) + "\n"


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


def report_text(d):
    """Match summaries first, then the level report (one read of the current file)."""
    cur, path = current_path(d)
    hist, prev, logs, _, _, lv = load(path)
    return (f"File: {path}\n\n" + account_line(load_account(d)) + "\n" +
            summary(cur, hist, prev, logs) + "\n" + lv_report(logs, lv))


def legend_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl, _ = load(path)
    return f"File: {path}\n\n" + legend_report(cur, logs, hl, pl, load_acct(d)[1])


def kills_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl, _ = load(path)
    acc, bases = load_acct(d)
    return account_line(acc, "kills") + "\n" + stat_report(cur, logs, hl, pl, 1, "KILLS", bases)


def wins_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl, _ = load(path)
    acc, bases = load_acct(d)
    return account_line(acc, "wins") + "\n" + stat_report(cur, logs, hl, pl, 2, "WINS", bases)


def m_text(d):
    cur, path = current_path(d)
    t = log_agg(load(path)[2])
    return f"MONTH {cur}  |  " + paint(f"KILLS {t[1]:,}  |  WINS {t[2]:,}") + "\n"


def lv_text(d):
    _, path = current_path(d)
    _, _, logs, _, _, lv = load(path)
    return lv_report(logs, lv)


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
    head = f"{'PERIOD':<{REF_W}} | {'FROM':<10} | {'GAINED':>7}"
    out = [f"# LEVELS GAINED  (today: {end}, current level: {f'{current:,}' if current else '-'})",
           head, "-" * len(head)]
    for label, start in windows:
        s = start.strftime(DAY_FMT)
        base = [n for k, n in points if k[:10] <= s]
        inside = [n for k, n in points if k[:10] > s]
        gained = current - (base[-1] if base else inside[0]) if points and (base or inside) else 0
        out.append(f"{label:<{REF_W}} | {s:<10} | {num(gained, 7)}")
    out.append("=" * len(head))
    return "\n".join(out) + "\n"


VIEWS = {"report": report_text, "l": legend_text, "k": kills_text, "w": wins_text,
         "m": m_text, "lv": lv_text}


def cmd_view(a):
    try:
        print(VIEWS[a.cmd](a.dir), end="")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_account(a):
    try:
        text, _, _ = account_cmd(a.dir, a.values, a.date, None, a.legend)
    except InputError:
        sys.exit("Format: account   or   account <kills> <wins> [legend] [level]   (e.g. account 12000 450)")
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(text, end="")


def cmd_base(a):
    try:
        print(base_cmd(a.dir, a.values, a.date), end="")
    except InputError:
        sys.exit("Format: base   or   base <legend> <kills> <wins>   (e.g. base wraith 3000 120)")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_c(_a):
    print(cheat_text(cli=True), end="")


def cmd_undo(a):
    try:
        print(undo(a.dir), end="")
    except ValueError as e:
        sys.exit(paint(str(e)))


USAGE_ADD = ('python apex_stats.py add <kills> <wins> [legend] [level] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]'
             '   # numeric 3rd value = level (700 absolute, +3 relative); legend defaults to "-"')
USAGE_NUM = ('python apex_stats.py <n> | <n>l | +<n> | <n>k | <n>w [--date "YYYY-MM-DD[ HH:MM]"]'
             "   # <n> = absolute level, <n>l (or +<n>) = n more levels, <n>k / <n>w = n kills / n wins only")
USAGE_REPORT = "python apex_stats.py report   # match summaries, followed by the level report (same as lv)"
USAGE_L = "python apex_stats.py l   # all-time kills and wins per legend (base + logged entries)"
USAGE_K = "python apex_stats.py k   # kills per legend: month, semiannual, annual, all-time + GRAND TOTAL"
USAGE_W = "python apex_stats.py w   # wins per legend: month, semiannual, annual, all-time + GRAND TOTAL"
USAGE_M = "python apex_stats.py m   # total kills and wins of the current file"
USAGE_LV = "python apex_stats.py lv   # levels gained over 1 week, 1/3/6 months and 1 year"
USAGE_UNDO = "python apex_stats.py undo   # remove the most recently added entry (repeat to go further back)"
USAGE_ACCOUNT = ('python apex_stats.py account [<kills> <wins> [legend] [level]] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]'
                 "   # show the totals; 1st time: save them; then: log the gain (new - saved) as a match")
USAGE_BASE = ('python apex_stats.py base [<legend> <kills> <wins>] [--date "YYYY-MM-DD[ HH:MM]"]'
              "   # list; 1st time: set a legend's all-time totals; then: log the gain (0 0 removes)")
USAGE_DIR = "python apex_stats.py --dir <path> ...   # data folder; default is ./apex_data next to the script"
USAGE_REPL = ("python apex_stats.py   # interactive mode: '<kills> <wins> [legend] [level]', '<n>', '<n>l', "
              "'<n>k', '<n>w' per line, account/base, report/l/k/w/m/lv/undo/c, "
              "'date YYYY-MM-DD' / 'date today', sticky legend, empty line to quit")
USAGE_C = "python apex_stats.py c   # quick-start cheat sheet: all inputs and commands"
USAGE = "\n  " + "\n  ".join((USAGE_ADD, USAGE_NUM, USAGE_REPORT, USAGE_L, USAGE_K, USAGE_W, USAGE_M,
                              USAGE_LV, USAGE_UNDO, USAGE_ACCOUNT, USAGE_BASE, USAGE_C, USAGE_DIR, USAGE_REPL))
# Next to the script, or next to the executable when frozen (PyInstaller unpacks __file__ into a temp dir)
_BASE = sys.executable if getattr(sys, "frozen", False) else __file__
DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(_BASE)), "apex_data")


def cheat_text(cli):
    """Full cheat sheet in the same layout as QUICK_GUIDE (title, [ SECTION ] rows, footer).
    cli=True for the command line, False for the interactive prompt."""
    a = "add " if cli else ""
    lvl = "python apex_stats.py " if cli else ""
    sections = (
        ("SETUP", (("account <kills> <wins>", "1st time: save your all-time totals (e.g. account 15000 800)"),
                   ("account <kills> <wins> [legend] [level]", "later: log the gain (new - saved) as a match"),
                   ("account", "show the saved global account totals"))),
        ("BASE", (("base <legend> <kills> <wins>", "1st time: set a legend's all-time totals (e.g. base wraith 3000 120)"),
                  ("base <legend> <kills> <wins>", "later: log the gain (new - current) as a match for it"),
                  ("base", "list the legends with a base and their all-time totals"))),
        ("MATCH", ((f"{a}<kills> <wins> [legend] [level]", "save a match (e.g. 5 1 wraith 57 | 5 1 57)"),
                   (f"{a}<kills> <wins> [legend] +<n>", "match + n levels (e.g. 5 1 wraith +3 | 5 1 +3)"))),
        ("QUICK", ((f"{lvl}<n>k", "n kills only: 0 wins, no legend (e.g. 5k)"),
                   (f"{lvl}<n>w", "n wins only: 0 kills, no legend (e.g. 1w)"))),
        ("LEVEL", ((f"{lvl}<n>", "set your absolute level (e.g. 700)"),
                   (f"{lvl}<n>l", "add n to the current level (e.g. 3l; +3 works too)"))),
        ("REPORT", (("report", "account totals + match summaries + level report"),
                    ("l", "all-time kills and wins per legend (base + logged)"),
                    ("k", "account kills + kills per legend (+ grand total)"),
                    ("w", "account wins + wins per legend (+ grand total)"),
                    ("m", "kills and wins this month"),
                    ("lv", "levels gained (1 week ... 1 year)"))),
        ("TOOLS", (("undo", "remove the last entry (repeatable)"),
                   (('--date "YYYY-MM-DD[ HH:MM]"', "date for add, account, base and quick entries") if cli else
                    ("date YYYY-MM-DD", "use this date for the next entries")),
                   *((() if cli else (("date today", "back to the system date"),))),
                   ("c", "this cheat sheet (help)"))),
    )
    w = max(len(c) for _, rows in sections for c, _ in rows) + 2
    out = [MENU_TITLE.rstrip("\n")]
    for tag, rows in sections:
        for i, (c, d) in enumerate(rows):
            cell = {"k": red, "w": green}.get(c, str)(c) + " " * (w - len(c))  # k red, w green
            out.append(f" {'[ ' + tag + ' ]' if i == 0 else '':<10}  {cell}{d}")
    out += ["-" * MENU_W,
            " [ RULES ]   - Kills first, then wins; a numeric 3rd value is the level, text is the legend.",
            "             - Legends are saved capitalized (wraith -> Wraith).",
            "             - Every match adds its kills and wins to its legend's all-time totals",
            "               (base + logged: l, k, w) and to the global account totals.",
            "             - account: the 1st time saves your totals; later it logs (new - saved) as a",
            "               match. Lower values only correct the totals. undo takes a match back out.",
            "             - base: the 1st time sets the legend's all-time totals (logged entries",
            "               included, nothing logged); later it logs (new - current) for that legend.",
            "             - Level <n> = absolute (never lower than the last one); <n>l adds n to it.",
            "             - <n>k and <n>w never use a legend.",
            "             - Entries cannot be dated in a month older than the newest data file.",
            "             - Numbers are shown with thousands separators (15,000); kills/wins may be typed so."]
    if not cli:
        out += ['             - Sticky legend: a legend you type is reused by later matches and account',
                '               entries that omit it, until you type another one ("-" clears it).']
    out += ["-" * MENU_W,
            " Run with no arguments for interactive mode." if cli else " Press Enter on an empty line to quit."]
    return color_quick(paint("\n".join(out) + "\n"))


def main():
    global COLOR
    COLOR = init_color()
    if len(sys.argv) == 1:
        interactive(DEFAULT_DIR)
        return
    argv = sys.argv[1:]
    first = argv[2] if argv[0] == "--dir" and len(argv) > 2 else argv[0]
    if LEVEL_RE.match(first) or QUICK_RE.match(first):  # "700", "3l", "+3", "5k", "1w"
        cmd_level(argv)
        return
    ap = argparse.ArgumentParser(usage=USAGE, description="Apex Legends stats tracker on .txt files")
    ap.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR,
                    help="data folder (default: ./apex_data next to the script)")
    sp = ap.add_subparsers(dest="cmd", required=True, metavar="{add,report,l,k,w,m,lv,undo,account,base,c}")
    p = sp.add_parser("add", prog="apex_stats.py add", usage="\n  " + USAGE_ADD,
                      help="record an entry (kills, wins, legend, level)")
    p.add_argument("values", nargs="+", metavar="<kills> <wins> [legend] [level]",
                   help="kills, wins, then legend and/or account level (numeric 3rd value = level; +<n> = relative)")
    p.add_argument("--l", dest="legend", metavar="NAME", help='legend (default: "-")')
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the entry (default: now)")
    p.set_defaults(fn=cmd_add)
    for name, usage, hlp in (("report", USAGE_REPORT, "match summaries + level report"),
                             ("l", USAGE_L, "all-time kills and wins per legend (base + logged)"),
                             ("k", USAGE_K, "kills per legend (month, semiannual, annual, all-time)"),
                             ("w", USAGE_W, "wins per legend (month, semiannual, annual, all-time)"),
                             ("m", USAGE_M, "total kills and wins of the current file"),
                             ("lv", USAGE_LV, "levels gained (report only)")):
        sp.add_parser(name, prog=f"apex_stats.py {name}", usage="\n  " + usage,
                      help=hlp).set_defaults(fn=cmd_view)
    sp.add_parser("undo", prog="apex_stats.py undo", usage="\n  " + USAGE_UNDO,
                  help="remove the most recently added entry").set_defaults(fn=cmd_undo)
    p = sp.add_parser("account", prog="apex_stats.py account", usage="\n  " + USAGE_ACCOUNT,
                      help="show / set the global account totals, or log the gain from new totals")
    p.add_argument("values", nargs="*", metavar="<kills> <wins> [legend] [level]",
                   help="new all-time account totals (omit to show them)")
    p.add_argument("--l", dest="legend", metavar="NAME", help="legend of the logged gain")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the logged gain (default: now)")
    p.set_defaults(fn=cmd_account)
    p = sp.add_parser("base", prog="apex_stats.py base", usage="\n  " + USAGE_BASE,
                      help="list the bases / set a legend's all-time totals, or log the gain")
    p.add_argument("values", nargs="*", metavar="<legend> <kills> <wins>",
                   help="legend and its all-time kills and wins (omit to list them)")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the logged gain (default: now)")
    p.set_defaults(fn=cmd_base)
    sp.add_parser("c", prog="apex_stats.py c", usage="\n  " + USAGE_C,
                  help="short quick-start cheat sheet").set_defaults(fn=cmd_c)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
