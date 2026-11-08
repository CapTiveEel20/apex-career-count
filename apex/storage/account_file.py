"""account_stats.txt: the global account totals (@ACCOUNT) and the legend bases (@BASE).

Reading and rendering only: commands change this file through the Ledger (storage/ledger.py).
"""
import os
from typing import NamedTuple, Optional

from apex.config import ACC_TAG, ACCOUNT_FILE, BASE_TAG, LEG_W
from apex.core.records import Stored


class AccountData(NamedTuple):
    """What account_stats.txt holds: account = the global totals (None if never set); bases = {legend: Stored}."""
    account: Optional[Stored]
    bases: dict


def account_path(d):
    return os.path.join(d, ACCOUNT_FILE)


def load_acct(d):
    """AccountData from account_stats.txt (one small read)."""
    acc, bases = None, {}
    try:
        with open(account_path(d), encoding="utf-8") as f:
            for line in f:
                c = line.split("|")
                tag = c[0].strip()
                try:
                    if tag == ACC_TAG and len(c) >= 3:
                        acc = Stored(int(c[1]), int(c[2]), c[3].strip() if len(c) > 3 else "")
                    elif tag == BASE_TAG and len(c) >= 4:
                        bases[c[1].strip()] = Stored(int(c[2]), int(c[3]), c[4].strip() if len(c) > 4 else "")
                except ValueError:
                    continue  # damaged line: skip it, keep the rest
    except FileNotFoundError:
        pass  # nothing saved yet; any other read error must not look like empty data
    except OSError as e:
        raise ValueError(f"Error: could not read {ACCOUNT_FILE} ({e}).") from e
    return AccountData(acc, bases)


def load_account(d):
    """The Stored global account totals, or None if never set."""
    return load_acct(d).account


def render_acct(acc, bases):
    """The text of account_stats.txt: the @ACCOUNT line (if set) and the @BASE lines."""
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
    return "\n".join(out) + "\n"
