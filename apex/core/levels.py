"""Account-level rules: levels never decrease; @LV pruning keeps one baseline day (no I/O)."""


def latest_level(logs, lv):
    """Current account level: the latest (= highest, levels never decrease) recorded; 0 if none."""
    return max([n for _, n in lv] + [e.level for e in logs], default=0)


def last_level(stamp, logs, lv):
    """Last (= highest) level recorded at or before stamp; 0 if none."""
    before = [n for _, n in lv] + [e.level for e in logs if e.level and e.date <= stamp]
    return max(before, default=0)


def check_level(level, stamp, logs, lv):
    """A level may never go down over time (0 = not recorded, always accepted)."""
    if not level:
        return
    last = last_level(stamp, logs, lv)
    if level < last:
        raise ValueError(f"Error: level {level:,} is lower than the last recorded level ({last:,}).")
    after = [(e.level, e.date) for e in logs if e.level and e.date > stamp]
    if after:
        nxt, when = min(after)
        if level > nxt:
            raise ValueError(f"Error: level {level:,} is higher than level {nxt:,} recorded later ({when}).")


def prune_lv(lv, cutoff):
    """Keep days after cutoff plus the latest earlier day as the baseline for the 1-year window."""
    old = [x for x in lv if x[0] <= cutoff]
    return old[-1:] + [x for x in lv if x[0] > cutoff]
