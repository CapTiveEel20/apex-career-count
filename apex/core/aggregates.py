"""Pure aggregation over log records: totals, per-legend totals, months and periods (no I/O)."""
import calendar
from datetime import date

from apex.config import NA, NO_LEGEND, SEMI_MONTHS, YEAR_MONTHS


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
