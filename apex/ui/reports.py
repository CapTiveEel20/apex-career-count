"""Read-only views: report, l, k, w, m, lv (each reads the current file once)."""
from datetime import date, timedelta

from apex.config import DAY_FMT, LEG_W, REF_W
from apex.core.aggregates import legend_periods, log_agg, months_ago, vadd, zero
from apex.display.colors import green, paint, red
from apex.display.messages import account_line
from apex.display.tables import LREP_HEAD, num, rep_cells, summary, vals_cells
from apex.storage.account_file import load_acct, load_account
from apex.storage.monthly_file import current_path, load


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


VIEWS = {"report": report_text, "l": legend_text, "k": kills_text, "w": wins_text,
         "m": m_text, "lv": lv_text}
