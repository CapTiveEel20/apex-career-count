"""'base' command: list, set or correct a legend's all-time totals, or log the gain."""
from apex.config import LEG_W, NO_LEGEND, REP, SRC_BASE
from apex.core.aggregates import legend_totals
from apex.core.parsing import LVL_TOKEN_RE, NUM_RE, InputError, clean, to_int
from apex.core.records import Tally
from apex.core.totals import FIRST, LOWERED, UNCHANGED, decide_totals
from apex.display.colors import green, paint, red
from apex.display.messages import fmt_saved
from apex.display.tables import REP_NAMES, rep_cells, vals_cells
from apex.services.entries import record_gain
from apex.storage.ledger import Ledger


def base_table(bases, logged):
    """'base': every legend with a base and its all-time totals (base + logged entries)."""
    head = f"{'# LEGEND':<{LEG_W}} | " + vals_cells(REP_NAMES, REP)
    dash = "-" * len(head)
    out = ["# LEGEND BASES  (all-time totals per legend: base + logged entries)", paint(head), dash]
    for leg, base in sorted(bases.items()):
        out.append(f"{leg:<{LEG_W}} | " + rep_cells(base.tally + logged.get(leg, Tally())))
    if not bases:
        out.append("(no bases set yet; use: base <legend> <kills> <wins>)")
    out.append("=" * len(head))
    return "\n".join(out) + "\n"


def base_cmd(d, args, when, confirm):
    """'base' lists the legend bases. 'base <legend> <kills> <wins>' = the legend's all-time totals:
    - legend not listed yet: they become its all-time totals (the entries already logged for it are
      included, nothing is added on top): the base stores only the part not covered by logged
      entries, and nothing is logged, so the account totals don't change;
    - legend already listed: like 'account', the gain (new - current all-time totals) is logged as
      a match for that legend through record_gain (so it reaches the account totals too; undo takes
      it back); lower values are a correction of the base, nothing logged;
    - 0 0 removes the base.
    Values lower than the current all-time totals (0 0 included) go ahead only if confirm() agrees,
    else ValueError(ABORTED). Setting, correcting and removing a base are undoable too (Ledger.change_base)."""
    with Ledger(d, when) as ledger:
        bases = ledger.bases
        if not args:
            return base_table(bases, legend_totals(ledger.current.hl, ledger.current.logs))
        if len(args) < 3 or not (NUM_RE.match(args[-2]) and NUM_RE.match(args[-1])):
            raise InputError()
        legend = clean(" ".join(args[:-2]), LEG_W)
        if legend == NO_LEGEND or LVL_TOKEN_RE.match(legend):
            raise InputError()
        kills, wins = to_int(args[-2]), to_int(args[-1])
        if kills < 0 or wins < 0:
            raise ValueError("Error: base kills and wins cannot be negative.")
        if not (kills or wins) and legend not in bases:
            raise ValueError(f"Error: {legend} has no base to remove.")
        m = ledger.open_month(any_month=True)  # base changes are not dated: never a closed month
        t = legend_totals(m.hl, m.logs).get(legend, Tally())
        lk, lw = t.kills, t.wins  # kills / wins already logged for this legend
        removing = not (kills or wins)
        if not removing and (kills < lk or wins < lw):
            raise ValueError(f"Error: {legend} already has " + paint(f"KILLS {lk:,} | WINS {lw:,}") +
                             " in logged entries; its all-time totals can't be lower.")
        current = bases[legend].tally + t if legend in bases else None  # all-time totals
        decision = decide_totals(Tally(kills=kills, wins=wins), current, confirm)
        if removing:
            ledger.remove_base(legend)
            return f"REMOVED - BASE {legend}\n"
        saved = ("SAVED - BASE  " + f"{legend}  " + paint(f"KILLS {kills:,}  |  WINS {wins:,}") +
                 "  (all-time totals of this legend)\n")
        if decision.kind == FIRST:  # set the all-time totals, nothing logged
            ledger.change_base(legend, kills - lk, wins - lw)
            return saved
        if decision.kind == LOWERED:  # correct the base, nothing logged
            ledger.change_base(legend, kills - lk, wins - lw)
            return saved.rstrip("\n") + "\n  (lower than the saved totals: corrected, nothing logged)\n"
        tk, tw = current.kills, current.wins
        if decision.kind == UNCHANGED:
            return (f"BASE  {legend}  already up to date: " + paint(f"KILLS {tk:,}  |  WINS {tw:,}") +
                    ", nothing logged.\n")
        dk, dw = decision.kills, decision.wins
        rec = record_gain(ledger, dk, dw, legend, source=SRC_BASE)
        line = (f"BASE  {legend}  " + red(f"KILLS {tk:,} -> {kills:,} (+{dk:,})") + "  |  " +
                green(f"WINS {tw:,} -> {wins:,} (+{dw:,})") + "\n")
        return line + fmt_saved(rec, ledger.level()) + "\n"
