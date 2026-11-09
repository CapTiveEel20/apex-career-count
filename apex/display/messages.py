"""Short terminal messages: the account-totals line, the SAVED confirmation and the undo report."""
from apex.config import SRC_ACCOUNT, SRC_BASE
from apex.display.colors import blue, cyan, green, orange, paint, purple, red


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
    account level (level = latest recorded, Saved.level; None = the entry's own level; 0 = '-')."""
    if rec.level_only:
        return "SAVED - " + orange(f"LEVEL {rec.level:,}") + f" ({rec.date[:10]})"
    lvl = rec.level if level is None else level
    return (f"SAVED  {rec.legend}  " + paint(f"KILLS {rec.kills:,}  WINS {rec.wins:,}") +
            "  " + level_txt(lvl) + f"  ({rec.date})")


def fmt_totals(totals):
    """TOTALS line of a saved match (ends with a newline); "" when totals is None (not a match).
    totals = MatchTotals: all-time, after the match; no legend = that part left out."""
    if not totals:
        return ""
    kw = lambda t: red(f"K: {t.kills:,}") + " " + green(f"W: {t.wins:,}")
    leg = f"[{totals.legend}] {kw(totals.legend_totals)} | " if totals.legend else ""
    return f"TOTALS -> {leg}" + purple("[ACCOUNT]") + " " + (kw(totals.account) if totals.account else "not set") + "\n"


def entry_line(e):
    """One log entry as undo shows it: date | legend | wins | kills | level."""
    return f"{e.date} | {e.legend} | " + paint(f"WINS {e.wins:,} | KILLS {e.kills:,}") + " | " + orange(f"LEVEL {e.level:,}")


def kw_values(kills, wins, sign=""):
    """'KILLS <k> | WINS <w>': the whole 'KILLS <k>' red, the whole 'WINS <w>' green (sign = "+" for gains)."""
    return red(f"KILLS {sign}{kills:,}") + " | " + green(f"WINS {sign}{wins:,}")


def fmt_previous(entry, change):
    """The most recent remaining action, labeled by type: [MATCH] (cyan), [ACCOUNT UPDATE] (purple),
    [BASE UPDATE] (blue) or [LEVEL UPDATE] (orange). entry / change = Month.last_action()."""
    if entry is None and change is None:
        return "none (nothing left to undo in this file)"
    if entry and entry.src == SRC_ACCOUNT:  # account gain (its snapshot shares the ID)
        return purple("[ACCOUNT UPDATE]") + f" {entry.date} | " + kw_values(entry.kills, entry.wins, "+")
    if entry and entry.src == SRC_BASE:  # base gain, logged for its legend
        return blue("[BASE UPDATE]") + f" {entry.date} | Legend: {entry.legend} | " + kw_values(entry.kills, entry.wins, "+")
    if entry and entry.level_only:
        return orange("[LEVEL UPDATE]") + f" {entry.date} | " + orange(f"LEVEL {entry.level:,}")
    if entry:
        level = " | " + orange(f"LEVEL {entry.level:,}") if entry.level else ""
        return cyan("[MATCH]") + f" {entry.date} | Legend: {entry.legend} | " + kw_values(entry.kills, entry.wins) + level
    old = change.old
    was = kw_values(old.kills, old.wins) if old else None
    if change.is_account:  # a change alone = the first account save or a confirmed lowering
        return purple("[ACCOUNT UPDATE]") + f" {change.date} | " + (
            f"totals changed (before: {was})" if was else "first save of the account totals")
    return blue("[BASE UPDATE]") + f" {change.date} | Legend: {change.target} | " + (
        f"base set, corrected or removed (stored base before: {was})" if was else "base set (none before)")


def fmt_undo(note, previous, entry=None, change=None, logged=None):
    """What undo reverted ('Undone: ...', with the file note), then the PREVIOUS LOG: the action that
    is now the most recent (previous = Month.last_action(), labeled by fmt_previous).
    entry / change = the records removed (an account gain removes both); logged = the Tally
    still logged for the legend of a reverted base change, shown on top of the restored base."""
    old = change.old if change else None
    if entry:
        acct = ("  " + purple("[ACCOUNT") + " restored to " + paint(f"KILLS {old.kills:,} | WINS {old.wins:,}") +
                purple("]")) if old else ""
        head = f"{entry_line(entry)}  ({note}){acct}"
    elif change.is_account:
        what = "restored to " + paint(f"KILLS {old.kills:,} | WINS {old.wins:,}") if old else "removed (not set before)"
        head = f"{change.date} | ACCOUNT {what}  ({note})"
    else:
        what = ("restored to " + paint(f"KILLS {old.kills + logged.kills:,} | WINS {old.wins + logged.wins:,}") + " (all-time)"
                if old else "removed (no base before)")
        head = f"{change.date} | BASE {change.target} {what}  ({note})"
    return f"Undone: {head}\nPREVIOUS LOG: {fmt_previous(*previous)}\n"
