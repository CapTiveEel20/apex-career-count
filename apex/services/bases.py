"""'base' command: list, set or correct a legend's all-time totals, or log the gain."""
from apex.config import DFMT, LEG_W, NO_LEGEND, REP, SRC_BASE
from apex.core.aggregates import legend_totals, zero
from apex.core.parsing import LVL_TOKEN_RE, NUM_RE, InputError, clean, parse_when, to_int
from apex.display.colors import green, paint, red
from apex.display.messages import fmt_saved
from apex.display.tables import REP_NAMES, rep_cells, vals_cells
from apex.services.entries import save_log
from apex.storage.account_file import load_acct, save_base
from apex.storage.atomic import write_atomic
from apex.storage.monthly_file import current_month, load, month_path, next_id, open_month, render


def legend_logged(d):
    """{legend: [logs, kills, wins]} of every logged entry, all-time (@HL + the current file; 1 read)."""
    cur = current_month(d)
    if not cur:
        return {}
    _, _, logs, hl, _, _, _ = load(month_path(d, cur))
    return legend_totals(hl, logs)


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


def record_base(d, opened, legend, kills, wins, acct, stamp):
    """Save a base change that logs nothing (set, correct, remove) so that undo can revert it:
    its @BU record (the previous base) goes into the month file first, then the new base is
    written to account_stats.txt."""
    month, (hist, prev, logs, hl, pl, lv, bu) = opened
    bu.append((next_id(logs, bu), stamp, legend, acct[1].get(legend)))
    write_atomic(month_path(d, month), render(month, hist, prev, logs, hl, pl, lv, bu))
    save_base(d, legend, kills, wins, acct)


def base_cmd(d, args, when=None):
    """'base' lists the legend bases. 'base <legend> <kills> <wins>' = the legend's all-time totals:
    - legend not listed yet: they become its all-time totals (the entries already logged for it are
      included, nothing is added on top): the base stores only the part not covered by logged
      entries, and nothing is logged, so the account totals don't change;
    - legend already listed: like 'account', the gain (new - current all-time totals) is logged as
      a match for that legend through save_log (so it reaches the account totals too; undo takes
      it back); lower values are a correction of the base, nothing logged;
    - 0 0 removes the base.
    Setting, correcting and removing a base are undoable too (record_base)."""
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
    if not (kills or wins) and legend not in bases:
        raise ValueError(f"Error: {legend} has no base to remove.")
    dt = parse_when(when)
    stamp = dt.strftime(DFMT)
    opened = open_month(d, dt, any_month=True)  # base changes are not dated: never a closed month
    if not (kills or wins):
        record_base(d, opened, legend, 0, 0, acct, stamp)
        return f"REMOVED - BASE {legend}\n"
    _, (_, _, logs, hl, _, _, _) = opened
    t = legend_totals(hl, logs).get(legend, zero())
    lk, lw = t[1], t[2]  # kills / wins already logged for this legend
    saved = ("SAVED - BASE  " + f"{legend}  " + paint(f"KILLS {kills:,}  |  WINS {wins:,}") +
             "  (all-time totals of this legend)\n")
    if kills < lk or wins < lw:
        raise ValueError(f"Error: {legend} already has " + paint(f"KILLS {lk:,} | WINS {lw:,}") +
                         " in logged entries; its all-time totals can't be lower.")
    if legend not in bases:  # first time: set the all-time totals, nothing logged
        record_base(d, opened, legend, kills - lk, wins - lw, acct, stamp)
        return saved
    bk, bw = bases[legend][:2]
    tk, tw = bk + lk, bw + lw  # current all-time totals
    dk, dw = kills - tk, wins - tw
    if dk < 0 or dw < 0:  # lower than before: correct the base, nothing logged
        record_base(d, opened, legend, kills - lk, wins - lw, acct, stamp)
        return saved.rstrip("\n") + "\n  (lower than the saved totals: corrected, nothing logged)\n"
    if not (dk or dw):
        return (f"BASE  {legend}  already up to date: " + paint(f"KILLS {tk:,}  |  WINS {tw:,}") +
                ", nothing logged.\n")
    _, _, level, rec = save_log(d, dk, dw, legend, when, account=acct[0], source=SRC_BASE)
    line = (f"BASE  {legend}  " + red(f"KILLS {tk:,} -> {kills:,} (+{dk:,})") + "  |  " +
            green(f"WINS {tw:,} -> {wins:,} (+{dw:,})") + "\n")
    return line + fmt_saved(rec, level) + "\n"
