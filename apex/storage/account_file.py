"""account_stats.txt: the global account totals (@ACCOUNT) and the legend bases (@BASE).

write_acct always rewrites both parts; save_account and save_base re-read the file first, so
neither drops the other's data.
"""
import os
from datetime import datetime

from apex.config import ACC_TAG, ACCOUNT_FILE, BASE_TAG, DFMT, LEG_W
from apex.storage.atomic import write_atomic


def account_path(d):
    return os.path.join(d, ACCOUNT_FILE)


def load_acct(d):
    """(account, bases) from account_stats.txt (one small read).
    account = (kills, wins, updated) or None if never set; bases = {legend: (kills, wins, updated)}."""
    acc, bases = None, {}
    try:
        with open(account_path(d), encoding="utf-8") as f:
            for line in f:
                c = line.split("|")
                tag = c[0].strip()
                try:
                    if tag == ACC_TAG and len(c) >= 3:
                        acc = int(c[1]), int(c[2]), c[3].strip() if len(c) > 3 else ""
                    elif tag == BASE_TAG and len(c) >= 4:
                        bases[c[1].strip()] = int(c[2]), int(c[3]), c[4].strip() if len(c) > 4 else ""
                except ValueError:
                    continue  # damaged line: skip it, keep the rest
    except OSError:
        pass
    return acc, bases


def load_account(d):
    """(kills, wins, updated) of the global account totals, or None if never set."""
    return load_acct(d)[0]


def write_acct(d, acc, bases):
    """Write account_stats.txt (1 atomic write): the @ACCOUNT line (if set) and the @BASE lines."""
    os.makedirs(d, exist_ok=True)
    head = f"{'# TAG':<9} | {'KILLS':>10} | {'WINS':>10} | UPDATED"
    bhead = f"{'# TAG':<9} | {'LEGEND':<{LEG_W}} | {'KILLS':>10} | {'WINS':>10} | UPDATED"
    eq = "=" * (len(bhead) + 12)
    out = [eq, "  APEX LEGENDS - ACCOUNT TOTALS (global, all-time) AND LEGEND BASES",
           "  Set with: account <kills> <wins>   |   base <legend> <kills> <wins>", eq, head, "-" * len(eq)]
    if acc:
        out.append(f"{ACC_TAG:<9} | {acc[0]:>10} | {acc[1]:>10} | {acc[2]}")
    out += ["", "# @BASE = per-legend all-time totals not covered by logged entries (set with base)", bhead, "-" * len(eq)]
    out += [f"{BASE_TAG:<9} | {leg:<{LEG_W}} | {k:>10} | {w:>10} | {upd}"
            for leg, (k, w, upd) in sorted(bases.items())]
    write_atomic(account_path(d), "\n".join(out) + "\n")


def save_account(d, kills, wins):
    """Write the global all-time account totals, keeping the legend bases (1 atomic write)."""
    if kills < 0 or wins < 0:
        raise ValueError("Error: account kills and wins cannot be negative.")
    stamp = f"{datetime.now():{DFMT}}"
    write_acct(d, (kills, wins, stamp), load_acct(d)[1])
    return kills, wins, stamp


def bump_account(d, kills, wins):
    """Add (or, with negative values, subtract) kills/wins to the saved global account totals.
    No-op when nothing changes or when the totals were never set; never below 0. Used by undo
    for entries flagged acc = 1 (save_log adds directly, after flagging the new entry)."""
    if not (kills or wins):
        return None
    acc = load_account(d)
    if acc is None:
        return None
    return save_account(d, max(0, acc[0] + kills), max(0, acc[1] + wins))


def restore_account(d, old):
    """Put back the previous global account totals exactly (old = (kills, wins, updated), None =
    never set), keeping the legend bases. Used by undo for account changes (1 read + 1 atomic write)."""
    write_acct(d, old, load_acct(d)[1])


def save_base(d, legend, kills, wins, acct=None):
    """Store (or, with 0 0, remove) a legend's base, keeping the account totals.
    acct = (account, bases) already loaded by the caller, so the file is not read twice."""
    acc, bases = acct or load_acct(d)
    if kills or wins:
        bases[legend] = (kills, wins, f"{datetime.now():{DFMT}}")
    else:
        bases.pop(legend, None)
    write_acct(d, acc, bases)


def restore_base(d, legend, old):
    """Put back a legend's previous base (old = (kills, wins, updated), None = it had none).
    Used by undo for a base change (1 read + 1 atomic write)."""
    acc, bases = load_acct(d)
    if old:
        bases[legend] = old
    else:
        bases.pop(legend, None)
    write_acct(d, acc, bases)
