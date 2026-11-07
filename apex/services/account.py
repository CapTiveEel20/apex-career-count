"""'account' command: show, first-time save, or log the gain (new - saved) as a match."""
from apex.core.parsing import NUM_RE, InputError, parse_extra, to_int
from apex.display.colors import green, paint, red
from apex.display.messages import account_line, fmt_saved
from apex.services.entries import save_log
from apex.storage.account_file import load_account, save_account


def account_cmd(d, args, when=None, default_legend=None, legend=None):
    """'account' shows the totals. 'account <kills> <wins> [legend] [level]':
    - first time (no totals yet): saves the totals, nothing is logged;
    - afterwards: logs the gain (new - saved) as one match entry through save_log, which then moves
      the totals to the new values (undo takes it back out);
    - new totals lower than the saved ones: a correction, the totals are replaced, nothing logged.
    default_legend = sticky legend (REPL); legend = --l (CLI). Returns (text, rec or None, typed legend)."""
    if not args:
        return account_line(load_account(d)), None, None
    if len(args) < 2 or not (NUM_RE.match(args[0]) and NUM_RE.match(args[1])):
        raise InputError()
    kills, wins = to_int(args[0]), to_int(args[1])
    try:
        typed, level, delta = parse_extra(args[2:])
    except ValueError:
        raise InputError() from None
    if legend:
        typed = legend
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    extra = bool(args[2:] or legend)
    acc = load_account(d)
    if acc is None:  # first time: just store the starting totals
        if extra:
            raise ValueError("Error: the first 'account <kills> <wins>' only saves your totals (no legend or level).")
        return "SAVED - " + account_line(save_account(d, kills, wins)), None, None
    dk, dw = kills - acc[0], wins - acc[1]
    if dk < 0 or dw < 0:  # lower than before: a correction, nothing to log
        if extra:
            raise ValueError("Error: these totals are lower than the saved ones (" +
                             paint(f"KILLS {acc[0]:,} | WINS {acc[1]:,}") +
                             "); a correction only replaces the totals (no legend or level).")
        return ("SAVED - " + account_line(save_account(d, kills, wins)).rstrip("\n") +
                "\n  (lower than the saved totals: corrected, nothing logged)\n"), None, None
    if not (dk or dw or level or delta):
        return ("ACCOUNT  already up to date: " + paint(f"KILLS {acc[0]:,}  |  WINS {acc[1]:,}") +
                ", nothing logged.\n"), None, None
    leg = typed if typed is not None else default_legend
    _, _, _, rec = save_log(d, dk, dw, leg, when, level, delta, account=acc)
    line = ("ACCOUNT  " + red(f"KILLS {acc[0]:,} -> {kills:,} (+{dk:,})") + "  |  " +
            green(f"WINS {acc[1]:,} -> {wins:,} (+{dw:,})") + "\n")
    return line + fmt_saved(rec) + "\n", rec, typed
