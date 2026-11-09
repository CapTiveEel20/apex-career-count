"""account_stats.txt: the global account totals (@ACCOUNT) and the legend bases (@BASE).

Reading and rendering only: commands change this file through the Ledger (storage/ledger.py).
A line that cannot be read is skipped with a warning and kept in the file as @BAD, so a later save
does not lose it.
"""
import os
import sys
from typing import NamedTuple, Optional

from apex.config import ACC_TAG, ACCOUNT_FILE, BASE_TAG, LEG_W
from apex.core.parsing import title_case
from apex.core.records import Stored


class AccountData(NamedTuple):
    """What account_stats.txt holds: account = the global totals (None if never set); bases = {legend: Stored};
    damaged = lines that could not be read, kept as they were."""
    account: Optional[Stored]
    bases: dict
    damaged: list

    @property
    def account_damaged(self):
        """True if the @ACCOUNT line could not be read: the totals are unknown, not 'never set'."""
        return any(line.split("|", 1)[0].strip() == ACC_TAG for line in self.damaged)


def account_path(d):
    return os.path.join(d, ACCOUNT_FILE)


def load_acct(d):
    """AccountData from account_stats.txt (one small read); each damaged line gets a warning on stderr."""
    acc, bases, damaged = None, {}, []
    try:
        with open(account_path(d), encoding="utf-8") as f:
            for line in f:
                c = line.split("|")
                tag = c[0].strip()
                try:
                    if tag == ACC_TAG:
                        acc = Stored(int(c[1]), int(c[2]), c[3].strip() if len(c) > 3 else "")
                    elif tag == BASE_TAG:
                        bases[title_case(c[1])] = Stored(int(c[2]), int(c[3]), c[4].strip() if len(c) > 4 else "")
                    elif tag == "@BAD":
                        damaged.append(line.split("|", 1)[1].strip())
                except (ValueError, IndexError):
                    damaged.append(line.strip())  # skip it, keep the rest
    except FileNotFoundError:
        pass  # nothing saved yet; any other read error must not look like empty data
    except OSError as e:
        raise ValueError(f"Error: could not read {ACCOUNT_FILE} ({e}).") from e
    for line in damaged:
        print(f"Warning: damaged line skipped in {ACCOUNT_FILE}: {line}", file=sys.stderr)
    return AccountData(acc, bases, damaged)


def load_account(d):
    """The Stored global account totals, or None if never set."""
    return load_acct(d).account


def render_acct(acc, bases, damaged=()):
    """The text of account_stats.txt: the @ACCOUNT line (if set), the @BASE lines and any @BAD lines."""
    head =f"{'# TAG':<9} | {'KILLS':>10} | {'WINS':>10} | UPDATED"
    bhead = f"{'# TAG':<9} | {'LEGEND':<{LEG_W}} | {'KILLS':>10} | {'WINS':>10} | UPDATED"
    eq = "=" * (len(bhead) + 12)
    out = [eq, "  APEX LEGENDS - ACCOUNT TOTALS (global, all-time) AND LEGEND BASES",
           "  Set with: account <kills> <wins>   |   base <legend> <kills> <wins>", eq, head, "-" * len(eq)]
    if acc:
        out.append(f"{ACC_TAG:<9} | {acc.kills:>10} | {acc.wins:>10} | {acc.updated}")
    out += ["", "# @BASE = per-legend all-time totals not covered by logged entries (set with base)", bhead, "-" * len(eq)]
    out += [f"{BASE_TAG:<9} | {leg:<{LEG_W}} | {k:>10} | {w:>10} | {upd}"
            for leg, (k, w, upd) in sorted(bases.items())]
    if damaged:  # only files with lines that could not be read have this section
        out += ["", "# @BAD = damaged lines, skipped when reading; fix or delete them by hand"]
        out += [f"{'@BAD':<9} | {line}" for line in damaged]
    return "\n".join(out) + "\n"
