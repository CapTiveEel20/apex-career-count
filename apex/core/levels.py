"""Account-level rules: a level goes down only when confirmed; @LV pruning keeps one baseline day (no I/O)."""
from apex.config import ABORTED


def _last_of(entries, lv):
    """Level of the most recent entry, else of the last carried @LV day (older than any entry); 0 if none."""
    if entries:
        return max(entries, key=lambda e: (e.date, e.id)).level
    return lv[-1][1] if lv else 0


def latest_level(logs, lv):
    """Current account level: the most recently recorded one; 0 if none."""
    return _last_of([e for e in logs if e.level], lv)


def last_level(stamp, logs, lv):
    """Most recent level recorded at or before stamp; 0 if none."""
    return _last_of([e for e in logs if e.level and e.date <= stamp], lv)


def check_level(level, stamp, logs, lv, confirm=None):
    """A level goes down over time only if confirm() agrees (None = never; 0 = not recorded, always accepted)."""
    if not level:
        return
    last = last_level(stamp, logs, lv)
    if level < last:
        if not confirm:
            raise ValueError(f"Error: level {level:,} is lower than the last recorded level ({last:,}).")
        if not confirm():
            raise ValueError(ABORTED)
    after = [(e.level, e.date) for e in logs if e.level and e.date > stamp]
    if after:
        nxt, when = min(after)
        if level > nxt:
            raise ValueError(f"Error: level {level:,} is higher than level {nxt:,} recorded later ({when}).")


def prune_lv(lv, cutoff):
    """Keep days after cutoff plus the latest earlier day as the baseline for the 1-year window."""
    old = [x for x in lv if x[0] <= cutoff]
    return old[-1:] + [x for x in lv if x[0] > cutoff]
