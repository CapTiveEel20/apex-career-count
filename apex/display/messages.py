"""One-line terminal messages: the account-totals line and the SAVED confirmation."""
from apex.config import NO_LEGEND
from apex.display.colors import orange, paint


def level_txt(level):
    """'LEVEL <n>' all orange (word and number); 'LEVEL -' when no level is recorded (0)."""
    return orange(f"LEVEL {level:,}" if level else "LEVEL -")


def account_line(acc, which="both", level=None):
    """One display line with the global account totals: which = 'kills', 'wins' or 'both';
    level (not None) appends the current account level ('account' command)."""
    if not acc:
        return paint("ACCOUNT  not set yet (use: account <kills> <wins>)") + "\n"
    k, w, upd = acc
    vals = {"kills": [f"KILLS {k:,}"], "wins": [f"WINS {w:,}"], "both": [f"KILLS {k:,}", f"WINS {w:,}"]}[which]
    lvl = "" if level is None else "  |  " + level_txt(level)
    note = f"  (global, all-time; updated {upd})" if upd else "  (global, all-time)"
    return paint("ACCOUNT  " + "  |  ".join(vals)) + lvl + note + "\n"


def logs_word(n):
    return f"{n:,} log" + ("" if n == 1 else "s")


def is_level_only(rec):
    return not rec[2] and not rec[3] and rec[4] and rec[1] == NO_LEGEND


def fmt_saved(rec, level=None):
    """SAVED line. Level-only updates show their level and day; matches show the current account
    level (level = latest recorded, from save_log; None = the entry's own level; 0 = '-')."""
    if is_level_only(rec):
        return "SAVED - " + orange(f"LEVEL {rec[4]:,}") + f" ({rec[0][:10]})"
    lvl = rec[4] if level is None else level
    return (f"SAVED  {rec[1]}  " + paint(f"KILLS {rec[2]:,}  WINS {rec[3]:,}") +
            "  " + level_txt(lvl) + f"  ({rec[0]})")
