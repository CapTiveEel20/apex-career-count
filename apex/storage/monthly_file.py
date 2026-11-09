"""Monthly data file (apex_stats_YYYY-MM.txt): render, parse, locate and roll over a month. Commands
change these files through the Ledger (storage/ledger.py).

Header lines (@FILE, @HIST, @PREV, @HL, @PL, @LV, @LL, @TK, @MB) carry the totals of earlier months forward, so
only the newest file is read ('report' alone also reads the older months, for its day windows and first level). @BU lines are the undo records (Change) of this file's base and
account changes (target @ACCOUNT = the global account totals before the change).
parse() dispatches on the first column and stops at the footer. A line it cannot read is skipped, and
kept in the file as @BAD so that a later save does not lose it.
"""
import os
import sys
from datetime import timedelta

from apex.config import (ACC_TAG, AGG, DAY_FMT, FNAME, FOOTER_MARK, FRE, LEG_W, LV_KEEP_DAYS, REF_W, SRC_LEVEL, SRC_MATCH,
                         TAG_W, YEAR_MONTHS)
from apex.core.aggregates import (day_levels, ints, last_logged, legend_agg, legend_totals, log_agg, midx,
                                  monthly_bests, top_matches)
from apex.core.levels import prune_lv
from apex.core.parsing import title_case
from apex.core.records import Change, Entry, LevelDay, Month, Stored, TopMatch
from apex.display.tables import SUM_HEAD, summary, vals_cells


def row(tag, ref, vals):
    return f"{tag:<{TAG_W}} | {ref:<{REF_W}} | " + vals_cells(vals)


def pl_row(m, leg, t):
    return f"{'@PL':<{TAG_W}} | {m:<7} | {leg:<{LEG_W}} | " + vals_cells(t)


def lv_row(day, n):
    return f"{'@LV':<{TAG_W}} | {day:<{REF_W}} | {n:>7}"


def ll_row(leg, day):
    return f"{'@LL':<{TAG_W}} | {leg:<{REF_W}} | {day}"


def tk_row(r, tag="@TK"):
    return f"{tag:<{TAG_W}} | {r.date:<16} | {r.legend:<{LEG_W}} | {r.kills:>5} | {r.wins:>5}"


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
    out += ["", "# @MB = all-time monthly bests (#1 match of each previous month), best first", TK_HEAD, dash]
    out += [tk_row(r, "@MB") for r in m.bests]
    if m.changes:  # only months with base or account changes have this section
        out += ["", "# @BU = base / @ACCOUNT changes of this month (undo puts the OLD values back; - = none)",
                BU_HEAD, dash]
        out += [bu_row(c) for c in m.changes]
    if m.damaged:  # only files with lines that could not be read have this section
        out += ["", "# @BAD = damaged lines, skipped when reading; fix or delete them by hand"]
        out += [f"{'@BAD':<{TAG_W}} | {line}" for line in m.damaged]
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
    return Entry(c[1].strip(), title_case(c[2]), kills, wins, lvl, lid, acc, src)


def parse(text):
    """The Month held by the text of one monthly file."""
    m = Month.empty()
    hist = m.hist
    for line in text.split("\n"):
        c = line.split("|")
        k = c[0].strip()
        try:
            if k == "L":
                m.logs.append(_entry(c, len(m.logs)))
            elif k == "@HIST":
                hist = ints(c[2:])
            elif k == "@PREV":
                m.prev.append((c[1].strip(), ints(c[2:])))
            elif k == "@HL":
                m.hl[title_case(c[1])] = ints(c[2:])
            elif k == "@PL":
                m.pl.append((c[1].strip(), title_case(c[2]), ints(c[3:])))
            elif k == "@LV":
                m.lv.append(LevelDay(c[1].strip(), int(c[2])))
            elif k == "@LL":
                m.ll[title_case(c[1])] = c[2].strip()
            elif k == "@TK":
                m.top.append(TopMatch(c[1].strip(), title_case(c[2]), int(c[3]), int(c[4])))
            elif k == "@MB":
                m.bests.append(TopMatch(c[1].strip(), title_case(c[2]), int(c[3]), int(c[4])))
            elif k == "@BU":
                old = None if c[4].strip() == "-" else Stored(int(c[4]), int(c[5]), c[6].strip())
                target = c[3].strip()
                m.changes.append(Change(int(c[1]), c[2].strip(), target if target == ACC_TAG else title_case(target), old))
            elif k == "@BAD":
                m.damaged.append(line.split("|", 1)[1].strip())
            elif k.startswith(FOOTER_MARK):
                break  # summary is recomputed: no need to read it
        except (ValueError, IndexError):
            m.damaged.append(line.strip())
    return m._replace(hist=hist)


def read_month(path):
    """(text, Month) of one monthly file; each damaged line gets a warning on stderr."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = parse(text)
    for line in m.damaged:
        print(f"Warning: damaged line skipped in {os.path.basename(path)}: {line}", file=sys.stderr)
    return text, m


def load(path):
    """The Month held by one monthly file."""
    _, m = read_month(path)
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


def older_logs(d, cur):
    """Log entries of every month before cur, oldest first."""
    months = sorted(m.group(1) for m in map(FRE.match, os.listdir(d)) if m)
    return [e for month in months if month < cur for e in load(month_path(d, month)).logs]


def carried_elsewhere(d, month, m):
    """True if deleting month's file loses nothing: the totals its Month m carries are what the newest
    earlier file carries forward (nothing, if there is none). False if an earlier file has gone."""
    older = sorted(x.group(1) for x in map(FRE.match, os.listdir(d)) if x and x.group(1) < month)
    before = load(month_path(d, older[-1])) if older else Month.empty()
    return m.hist == before.hist + log_agg(before.logs)


def load_current(d):
    """(month, path, Month) of the newest file (1 read); ValueError if there is none."""
    cur = current_month(d)
    if not cur:
        raise ValueError("No data recorded yet.")
    path = month_path(d, cur)
    return cur, path, load(path)


def roll_over(cur, month, day, m):
    """Month of the new file `month` (newer than cur): the totals of cur are carried into its
    header, and its log entries and changes start empty. day = date of the new record."""
    ni = midx(month)
    keep = lambda mo: ni - midx(mo) < YEAR_MONTHS
    hist = m.hist + log_agg(m.logs)
    prev = [(mo, v) for mo, v in m.prev + [(cur, log_agg(m.logs))] if keep(mo)]
    la = legend_agg(m.logs)
    hl = legend_totals(m.hl, m.logs)
    pl = [(mo, leg, t) for mo, leg, t in m.pl + [(cur, leg, la[leg]) for leg in sorted(la)] if keep(mo)]
    cutoff = (day - timedelta(days=LV_KEEP_DAYS)).strftime(DAY_FMT)
    lv = prune_lv(m.lv + [LevelDay(*x) for x in sorted(day_levels(m.logs).items())], cutoff)
    return Month(hist, prev, [], hl, pl, lv, [], last_logged(m.ll, m.logs), top_matches(m.top, m.logs),
                 monthly_bests(m.bests, m.logs), [])
