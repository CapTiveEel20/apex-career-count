"""'account' command: show, first-time save, or log the gain (new - saved) as a match; 'accountl': set the level."""
from apex.config import ABORTED, SRC_ACCOUNT
from apex.core.levels import last_level
from apex.core.parsing import NUM_RE, InputError, parse_level, to_int
from apex.core.records import Tally
from apex.core.totals import FIRST, LOWERED, UNCHANGED, decide_totals
from apex.display.colors import green, paint, red
from apex.display.messages import account_line, fmt_saved, level_txt
from apex.services.entries import record_gain, record_level
from apex.storage.ledger import Ledger


def accountl_cmd(d, args, when, confirm):
    """'accountl <n>', 'accountl <level> <tier>' or 'accountl <level> tier <tier>': set the account level;
    a level lower than the current one needs confirm()."""
    level = parse_level(args)
    with Ledger(d, when) as ledger:
        m = ledger.open_month()
        if level < last_level(ledger.stamp, m.logs, m.lv) and not confirm():
            raise ValueError(ABORTED)
        return fmt_saved(record_level(ledger, level)) + "\n"


def account_cmd(d, args, when, confirm):
    """'account' shows the totals. 'account <kills> <wins> [level]' (level as in parse_level):
    - level given: recorded first (an equal level logs nothing); confirm() is asked once for the
      whole command if the level or the totals would go down, so nothing is half applied;
    - first time (no totals yet): saves the totals, nothing is logged;
    - afterwards: logs the gain (new - saved) as one entry with no legend (SRC account) through
      record_gain, which then moves the totals to the new values (undo takes it back out);
    - new totals lower than the saved ones: confirm() is asked; if it agrees they replace the saved
      ones, nothing is logged (undo restores the old totals); if not, ValueError(ABORTED).
    Every ACCOUNT line also shows the current account level. Returns the text to print."""
    if not args:
        with Ledger(d) as ledger:
            return account_line(ledger.account, level=ledger.level())
    if len(args) < 2 or not all(NUM_RE.match(a) for a in args[:2]):
        raise InputError()
    kills, wins = to_int(args[0]), to_int(args[1])
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    new_level = parse_level(args[2:]) if len(args) > 2 else 0
    with Ledger(d, when) as ledger:
        last = 0
        if new_level:
            m = ledger.open_month()
            last = last_level(ledger.stamp, m.logs, m.lv)
        acc = ledger.account
        decision = decide_totals(Tally(kills=kills, wins=wins), acc, confirm, also_lower=new_level < last)
        head = ""
        if new_level and new_level != last:
            head = fmt_saved(record_level(ledger, new_level)) + "\n"
        if decision.kind in (FIRST, LOWERED):  # replaces the totals, undoable, nothing logged
            return head + "SAVED - " + account_line(ledger.change_account(kills, wins), level=ledger.level())
        if decision.kind == UNCHANGED:
            return (head + "ACCOUNT  already up to date: " + paint(f"KILLS {acc.kills:,}  |  WINS {acc.wins:,}") +
                    "  |  " + level_txt(ledger.level()) + ", nothing logged.\n")
        dk, dw = decision.kills, decision.wins
        rec = record_gain(ledger, dk, dw, source=SRC_ACCOUNT)
        level = ledger.level()
        line = ("ACCOUNT  " + red(f"KILLS {acc.kills:,} -> {kills:,} (+{dk:,})") + "  |  " +
                green(f"WINS {acc.wins:,} -> {wins:,} (+{dw:,})") + "  |  " + level_txt(level) + "\n")
        return head + line + fmt_saved(rec, level) + "\n"
