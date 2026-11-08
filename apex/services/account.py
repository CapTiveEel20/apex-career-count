"""'account' command: show, first-time save, or log the gain (new - saved) as a match; 'accountl': set the level."""
from apex.config import ABORTED, ACC_TAG, DFMT, SRC_ACCOUNT, SRC_LEVEL
from apex.core.levels import last_level
from apex.core.parsing import NUM_RE, InputError, parse_when, to_int
from apex.display.colors import green, paint, red
from apex.display.messages import account_line, fmt_saved, level_txt
from apex.services.entries import current_level, save_log
from apex.storage.account_file import load_account, save_account
from apex.storage.monthly_file import open_month, save_change


def record_account(d, when=None, old=None):
    """Undo record of an account save that logs nothing (first save, or a confirmed lowering): a Change
    of the account totals holding the previous ones (old; None = never set), written to the month
    file before account_stats.txt changes."""
    dt = parse_when(when)
    month, m = open_month(d, dt, any_month=True)
    save_change(d, month, m, dt.strftime(DFMT), ACC_TAG, old)


def accountl_cmd(d, args, when, confirm):
    """'accountl <n>': set the absolute account level; a level lower than the current one needs confirm()."""
    if len(args) != 1 or not NUM_RE.match(args[0]):
        raise InputError()
    rec = save_log(d, 0, 0, None, when, _level_arg(args[0]), source=SRC_LEVEL, confirm=confirm)[3]
    return fmt_saved(rec) + "\n"


def _level_arg(token):
    n = to_int(token)
    if n < 1:
        raise ValueError("Error: the level must be 1 or higher.")
    return n


def account_cmd(d, args, when, confirm):
    """'account' shows the totals. 'account <kills> <wins> [level]':
    - level given: recorded first (an equal level logs nothing); confirm() is asked once for the
      whole command if the level or the totals would go down, so nothing is half applied;
    - first time (no totals yet): saves the totals, nothing is logged;
    - afterwards: logs the gain (new - saved) as one entry with no legend (SRC account) through
      save_log, which then moves the totals to the new values (undo takes it back out);
    - new totals lower than the saved ones: confirm() is asked; if it agrees they replace the saved
      ones, nothing is logged (undo restores the old totals); if not, ValueError(ABORTED).
    Every ACCOUNT line also shows the current account level. Returns the text to print."""
    if not args:
        return account_line(load_account(d), level=current_level(d))
    if len(args) not in (2, 3) or not all(NUM_RE.match(a) for a in args):
        raise InputError()
    kills, wins = to_int(args[0]), to_int(args[1])
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    new_level = _level_arg(args[2]) if len(args) == 3 else 0
    last = 0
    if new_level:
        dt = parse_when(when)
        m = open_month(d, dt)[1]
        last = last_level(dt.strftime(DFMT), m.logs, m.lv)
    acc = load_account(d)
    if (new_level < last or (acc and (kills < acc[0] or wins < acc[1]))) and not confirm():
        raise ValueError(ABORTED)
    head = ""
    if new_level and new_level != last:  # first: a level error leaves the totals untouched
        head = fmt_saved(save_log(d, 0, 0, None, when, new_level, source=SRC_LEVEL, confirm=lambda: True)[3]) + "\n"
    if acc is None:  # first time: just store the starting totals (undoable: the @BU record goes first)
        record_account(d, when)
        return head + "SAVED - " + account_line(save_account(d, kills, wins), level=current_level(d))
    dk, dw = kills - acc[0], wins - acc[1]
    if dk < 0 or dw < 0:  # a confirmed lowering of the all-time totals logs nothing
        record_account(d, when, acc)
        return head + "SAVED - " + account_line(save_account(d, kills, wins), level=current_level(d))
    if not (dk or dw):
        return (head + "ACCOUNT  already up to date: " + paint(f"KILLS {acc[0]:,}  |  WINS {acc[1]:,}") +
                "  |  " + level_txt(current_level(d)) + ", nothing logged.\n")
    _, _, level, rec, _ = save_log(d, dk, dw, None, when, account=acc, source=SRC_ACCOUNT)
    line = ("ACCOUNT  " + red(f"KILLS {acc[0]:,} -> {kills:,} (+{dk:,})") + "  |  " +
            green(f"WINS {acc[1]:,} -> {wins:,} (+{dw:,})") + "  |  " + level_txt(level) + "\n")
    return head + line + fmt_saved(rec, level) + "\n"
