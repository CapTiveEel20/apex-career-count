"""The decision shared by 'account' and 'base': typed all-time totals against the current ones (no I/O)."""
from typing import NamedTuple

from apex.config import ABORTED

FIRST, LOWERED, UNCHANGED, GAINED = "first", "lowered", "unchanged", "gained"


class Decision(NamedTuple):
    """kind = FIRST, LOWERED, UNCHANGED or GAINED; kills, wins = typed minus current (0 0 if FIRST)."""
    kind: str
    kills: int
    wins: int


def decide_totals(typed, current, confirm, also_lower=False):
    """Compare typed with current (both have .kills and .wins; current None = never set). Downgrade
    Protection: values going down need confirm(), else ValueError(ABORTED). also_lower = another part of
    the same command goes down too, covered by the same single confirm()."""
    dk, dw = (typed.kills - current.kills, typed.wins - current.wins) if current else (0, 0)
    lowered = dk < 0 or dw < 0
    if (lowered or also_lower) and not confirm():
        raise ValueError(ABORTED)
    if current is None:
        return Decision(FIRST, 0, 0)
    if lowered:
        return Decision(LOWERED, dk, dw)
    return Decision(GAINED if dk or dw else UNCHANGED, dk, dw)
