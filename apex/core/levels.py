"""Account-level rules: the current and last recorded level, the check against later levels; @LV pruning
keeps one baseline day (no I/O)."""
from apex.config import LEVELS_PER_TIER


def absolute_level(level, tier):
    """The absolute level of a level within a tier (200 in tier 2 = 700)."""
    return (tier - 1) * LEVELS_PER_TIER + level


def _level_parts(level):
    """(level within its tier, tier) of an absolute level of 1 or higher."""
    tier = (level - 1) // LEVELS_PER_TIER + 1
    return level - (tier - 1) * LEVELS_PER_TIER, tier


def level_name(level):
    """'Level 200 Tier 2' for the absolute level 700; 'Level -' for 0 (none recorded)."""
    if not level:
        return "Level -"
    n, tier = _level_parts(level)
    return f"Level {n} Tier {tier}"


def level_short(level):
    """'200 T2' for the absolute level 700, for narrow table columns; '-' for 0."""
    if not level:
        return "-"
    n, tier = _level_parts(level)
    return f"{n} T{tier}"


def _last_of(entries, lv):
    """Level of the most recent entry, else of the last carried @LV day (older than any entry); 0 if none."""
    if entries:
        return max(entries, key=lambda e: (e.date, e.id)).level
    return lv[-1].level if lv else 0


def first_level(logs, lv):
    """The first level ever recorded, from the entries of every available month and the carried @LV
    days (an earlier @LV day wins only if its month's file is gone); 0 if none."""
    first = min((e for e in logs if e.level), key=lambda e: (e.date, e.id), default=None)
    if lv and (first is None or lv[0].day < first.date[:10]):
        return lv[0].level
    return first.level if first else 0


def latest_level(logs, lv):
    """Current account level: the most recently recorded one; 0 if none."""
    return _last_of([e for e in logs if e.level], lv)


def last_level(stamp, logs, lv):
    """Most recent level recorded at or before stamp; 0 if none."""
    return _last_of([e for e in logs if e.level and e.date <= stamp], lv)


def check_later(level, stamp, logs):
    """A level dated stamp cannot be higher than a level recorded after it."""
    after =[(e.level, e.date) for e in logs if e.level and e.date > stamp]
    if after:
        nxt, when = min(after)
        if level > nxt:
            raise ValueError(f"Error: {level_name(level)} is higher than {level_name(nxt)} recorded later ({when}).")


def prune_lv(lv, cutoff):
    """Keep days after cutoff plus the latest earlier day as the baseline for the 1-year window."""
    old = [x for x in lv if x.day <= cutoff]
    return old[-1:] + [x for x in lv if x.day > cutoff]
