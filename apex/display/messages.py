"""One-line terminal messages: the account-totals line and the SAVED confirmation."""
from apex.config import NO_LEGEND
from apex.display.colors import paint


def account_line(acc, which="both"):
    """One display line with the global account totals: which = 'kills', 'wins' or 'both'."""
    if not acc:
        return paint("ACCOUNT  not set yet (use: account <kills> <wins>)") + "\n"
    k, w, upd = acc
    vals = {"kills": [f"KILLS {k:,}"], "wins": [f"WINS {w:,}"], "both": [f"KILLS {k:,}", f"WINS {w:,}"]}[which]
    note = f"  (global, all-time; updated {upd})" if upd else "  (global, all-time)"
    return paint("ACCOUNT  " + "  |  ".join(vals)) + note + "\n"


def logs_word(n):
    return f"{n:,} log" + ("" if n == 1 else "s")


def is_level_only(rec):
    return not rec[2] and not rec[3] and rec[4] and rec[1] == NO_LEGEND


def fmt_saved(rec):
    if is_level_only(rec):
        return f"SAVED - LEVEL {rec[4]:,} ({rec[0][:10]})"
    return (f"SAVED  {rec[1]}  " + paint(f"WINS {rec[3]:,}  KILLS {rec[2]:,}") +
            f"  LEVEL {rec[4]:,}  ({rec[0]})")
