"""Pure aggregation over log entries (records.Entry): totals, per-legend totals, months and periods (no I/O)."""
from apex.config import (NA, NO_LEGEND, SEMI_MONTHS, SRC_ACCOUNT, SRC_CLAIM, SRC_MATCH, TOP_MATCHES, TOP_MONTH_BESTS,
                         YEAR_MONTHS)
from apex.core.records import LegendRow, Periods, Tally, TopMatch


def ints(cells):
    if len(cells) < NA:
        raise ValueError("missing columns")
    return Tally(*(int(x) for x in cells[:NA]))


def midx(month):
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def log_agg(logs):
    """Tally (entries, kills, wins) of what the entries add to the account and to 'report': all but the
    claimed parts of base gains (SRC_CLAIM), which an account gain already counted."""
    logs = [e for e in logs if e.src != SRC_CLAIM]
    return Tally(len(logs), sum(e.kills for e in logs), sum(e.wins for e in logs))


def legend_agg(logs):
    d = {}
    for e in logs:
        d[e.legend] = d.get(e.legend, Tally()) + Tally(1, e.kills, e.wins)
    return d


def legend_totals(hl, logs):
    """{legend: Tally} logged all-time: the carried @HL totals + the file's entries."""
    out = dict(hl)
    for leg, t in legend_agg(logs).items():
        out[leg] = out.get(leg, Tally()) + t
    return out


def unclaimed(logs, changes):
    """Tally(0, kills, wins) that the month's account gains (SRC_ACCOUNT entries) added and that no
    legend's base gain has claimed yet (SRC_CLAIM entries); kills and wins apart, each never below 0.
    Only records after the month's last account change that is not a gain count: a first save or a
    confirmed lowering sets the account totals anew. Worked out from the records each time, never
    stored: undo takes the newest record out first, so it stays exact."""
    shared = {e.id for e in logs}  # a gain's snapshot shares its entry's ID
    reset = max((c.id for c in changes if c.is_account and c.id not in shared), default=0)
    after = [e for e in logs if e.id > reset]
    added = [e for e in after if e.src == SRC_ACCOUNT]
    claimed = [e for e in after if e.src == SRC_CLAIM]
    kills = sum(e.kills for e in added) - sum(e.kills for e in claimed)
    wins = sum(e.wins for e in added) - sum(e.wins for e in claimed)
    return Tally(0, max(0, kills), max(0, wins))


def last_logged(ll, logs):
    """{legend: date and time of its last match}: the carried @LL values + the file's match entries
    (SRC match; account / base gains and level updates do not count). Entries without a legend are
    left out. Older @LL values hold only the day; they still compare correctly as text."""
    out = dict(ll)
    for e in logs:
        if e.src == SRC_MATCH and e.legend != NO_LEGEND:
            out[e.legend] = max(out.get(e.legend, ""), e.date)
    return out


def top_matches(top, logs, n=TOP_MATCHES):
    """All-time leaderboard of single matches by kills, [TopMatch], best first:
    the carried @TK rows + the file's match entries (SRC match; account / base gains are not
    matches). Ties: the earlier match ranks first. Matches with 0 kills never qualify."""
    rows = list(top) + [TopMatch(e.date, e.legend, e.kills, e.wins) for e in logs if e.src == SRC_MATCH and e.kills > 0]
    return sorted(rows, key=lambda r: (-r.kills, r.date))[:n]


def monthly_bests(bests, logs, n=TOP_MONTH_BESTS):
    """All-time monthly bests after a month closes, [TopMatch], best first: the month's #1 match
    (of logs) joins bests if there is room or its kills beat the lowest row, which it then replaces.
    Ties: the earlier match ranks first."""
    best = top_matches([], logs, 1)
    if not best or (len(bests) >= n and best[0].kills <= min(r.kills for r in bests)):
        return list(bests)
    return sorted(list(bests) + best, key=lambda r: (-r.kills, r.date))[:n]


def day_levels(logs):
    """day -> last level recorded that day (level 0 = not recorded)."""
    return {e.date[:10]: e.level for e in sorted(logs, key=lambda e: (e.date, e.id)) if e.level}


def periods(month, cur, hist, prev):
    """Periods of the month; prev = [(month, Tally)]."""
    ci = midx(month)
    semi = year = cur
    for m, v in prev:
        d = ci - midx(m)
        if d < SEMI_MONTHS:
            semi = semi + v
        if d < YEAR_MONTHS:
            year = year + v
    return Periods(cur, semi, year, hist + cur)


def legend_periods(month, logs, hl, pl, bases=None):
    """[LegendRow] for real legends only:
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
        ps = periods(month, la.get(leg, Tally()), hl.get(leg, Tally()), by_leg.get(leg, []))
        b = bases.get(leg)
        if b:
            ps = ps._replace(alltime=ps.alltime + b.tally)
        out.append(LegendRow(leg, ps))
    return out
