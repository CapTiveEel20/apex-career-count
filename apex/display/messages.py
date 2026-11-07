"""Short terminal messages: the account-totals line, the SAVED confirmation and the undo report."""
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


def fmt_saved(rec, level=None):
    """SAVED line of an Entry. Level-only updates show their level and day; matches show the current
    account level (level = latest recorded, from save_log; None = the entry's own level; 0 = '-')."""
    if rec.level_only:
        return "SAVED - " + orange(f"LEVEL {rec.level:,}") + f" ({rec.date[:10]})"
    lvl = rec.level if level is None else level
    return (f"SAVED  {rec.legend}  " + paint(f"KILLS {rec.kills:,}  WINS {rec.wins:,}") +
            "  " + level_txt(lvl) + f"  ({rec.date})")


def entry_line(e):
    """One log entry as undo shows it: date | legend | wins | kills | level."""
    return f"{e.date} | {e.legend} | " + paint(f"WINS {e.wins:,} | KILLS {e.kills:,}") + " | " + orange(f"LEVEL {e.level:,}")


def fmt_undo(note, latest, entry=None, change=None, logged=None):
    """What undo reverted ('Undone: ...', with the file note), then the entry that is now the latest.
    entry / change = the records removed (an account gain removes both); logged = the (kills, wins)
    still logged for the legend of a reverted base change, shown on top of the restored base."""
    old = change.old if change else None
    if entry:
        acct = ("  [ACCOUNT restored to " + paint(f"KILLS {old[0]:,} | WINS {old[1]:,}") + "]") if old else ""
        head = f"{entry_line(entry)}  ({note}){acct}"
    elif change.is_account:
        what = "restored to " + paint(f"KILLS {old[0]:,} | WINS {old[1]:,}") if old else "removed (not set before)"
        head = f"{change.date} | ACCOUNT {what}  ({note})"
    else:
        what = ("restored to " + paint(f"KILLS {old[0] + logged[0]:,} | WINS {old[1] + logged[1]:,}") + " (all-time)"
                if old else "removed (no base before)")
        head = f"{change.date} | BASE {change.target} {what}  ({note})"
    now = entry_line(latest) if latest else "none (no entries left in this file)"
    return f"Undone: {head}\nLatest entry now: {now}\n"
