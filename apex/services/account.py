"""'account' command: show, first-time save, or log the gain (new - saved) as a match."""
from apex.config import ACC_TAG, DFMT, SRC_ACCOUNT
from apex.core.parsing import NUM_RE, InputError, parse_when, to_int
from apex.display.colors import green, paint, red
from apex.display.messages import account_line, fmt_saved, level_txt
from apex.services.entries import current_level, save_log
from apex.storage.account_file import load_account, save_account
from apex.storage.atomic import write_atomic
from apex.storage.monthly_file import month_path, next_id, open_month, render


def record_account(d, when=None):
    """Undo record of a first-time account save (it logs nothing): an @BU line with legend @ACCOUNT
    and no old totals, written to the month file before account_stats.txt changes."""
    dt = parse_when(when)
    month, (hist, prev, logs, hl, pl, lv, bu) = open_month(d, dt, any_month=True)
    bu.append((next_id(logs, bu), dt.strftime(DFMT), ACC_TAG, None))
    write_atomic(month_path(d, month), render(month, hist, prev, logs, hl, pl, lv, bu))


def account_cmd(d, args, when=None):
    """'account' shows the totals. 'account <kills> <wins>' (kills and wins only, nothing else):
    - first time (no totals yet): saves the totals, nothing is logged;
    - afterwards: logs the gain (new - saved) as one entry with no legend (SRC account) through
      save_log, which then moves the totals to the new values (undo takes it back out);
    - new totals lower than the saved ones: an error, the update is aborted (saved totals kept).
    Every ACCOUNT line also shows the current account level. Returns the text to print."""
    if not args:
        return account_line(load_account(d), level=current_level(d))
    if len(args) != 2 or not (NUM_RE.match(args[0]) and NUM_RE.match(args[1])):
        raise InputError()
    kills, wins = to_int(args[0]), to_int(args[1])
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    acc = load_account(d)
    if acc is None:  # first time: just store the starting totals (undoable: the @BU record goes first)
        record_account(d, when)
        return "SAVED - " + account_line(save_account(d, kills, wins), level=current_level(d))
    dk, dw = kills - acc[0], wins - acc[1]
    if dk < 0 or dw < 0:  # all-time totals never go down: abort, the saved totals are kept
        raise ValueError(f"Error: KILLS {kills:,} | WINS {wins:,} is lower than the saved account totals "
                         f"(KILLS {acc[0]:,} | WINS {acc[1]:,}); nothing changed.")
    if not (dk or dw):
        return ("ACCOUNT  already up to date: " + paint(f"KILLS {acc[0]:,}  |  WINS {acc[1]:,}") +
                "  |  " + level_txt(current_level(d)) + ", nothing logged.\n")
    _, _, level, rec = save_log(d, dk, dw, None, when, account=acc, source=SRC_ACCOUNT)
    line = ("ACCOUNT  " + red(f"KILLS {acc[0]:,} -> {kills:,} (+{dk:,})") + "  |  " +
            green(f"WINS {acc[1]:,} -> {wins:,} (+{dw:,})") + "  |  " + level_txt(level) + "\n")
    return line + fmt_saved(rec, level) + "\n"
