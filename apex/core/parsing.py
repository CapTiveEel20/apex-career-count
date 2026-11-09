"""User-input parsing: number/level/quick tokens, legend names, the [legend] of a match, dates."""
import re
from datetime import datetime

from apex.config import DAY_FMT, DFMT, LEVELS_PER_TIER, MAX_LEVEL, MAX_TIER, NO_LEGEND
from apex.core.levels import absolute_level
from apex.core.records import Quick

NUM_RE = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)$")  # kills/wins: "15000" or "15,000"
QUICK_RE = re.compile(r"^\+?(\d+)([kwl])$", re.IGNORECASE)  # quick-add: "5k" kills, "1w" wins, "3l" +3 levels
QUICK_ORDER = "kwl"  # the order quick tokens are typed in
LVL_TOKEN_RE = re.compile(r"^[+-]?\d+$")  # a number where a legend is expected ("57", "+3", "-5"): rejected


class InputError(ValueError):
    """Unrecognized command or malformed input: the REPL answers with the help menu."""


def parse_quick(tokens):
    """A quick entry -> Quick; None if tokens do not start with one. <n>k [<n>w] [<n>l] [legend]: any
    of the three may be omitted, the others keep that order ("5k 2l wraith"). "3l" alone never takes
    a legend. ValueError for a wrong order, a repeated kind, n below 1, anything after a lone "3l"
    and (from parse_legend) for a number or quick token among the legend tokens."""
    hits = []
    for token in tokens:
        m = QUICK_RE.match(token)
        if not m:
            break
        hits.append((m.group(2).lower(), int(m.group(1))))
    if not hits:
        return None
    kinds = [kind for kind, _ in hits]
    if kinds != sorted(set(kinds), key=QUICK_ORDER.index):
        raise ValueError("Error: use <n>k, <n>w and <n>l once each, in that order (e.g. 5k 1w 2l wraith).")
    if any(n < 1 for _, n in hits):
        raise ValueError("Error: <n>k, <n>w and <n>l need n of 1 or higher.")
    rest = tokens[len(hits):]
    if kinds == ["l"] and rest:
        raise ValueError("Error: <n>l takes no legend or other input (e.g. 3l).")
    counts = dict(hits)
    return Quick(counts.get("k", 0), counts.get("w", 0), counts.get("l", 0), parse_legend(rest))


def to_int(s):
    """Whole number from user input, with or without thousands separators ("15,000")."""
    return int(s.replace(",", ""))


def parse_level(tokens):
    """Level tokens -> the absolute level: '<absolute>', '<level> <tier>' or '<level> tier <tier>'.
    InputError if they are none of these; ValueError for a value out of range."""
    if len(tokens) == 3 and tokens[1].lower() == "tier":
        tokens = [tokens[0], tokens[2]]
    if len(tokens) not in (1, 2) or not all(NUM_RE.match(t) for t in tokens):
        raise InputError()
    if len(tokens) == 1:
        level = to_int(tokens[0])
        if not 1 <= level <= MAX_LEVEL:
            raise ValueError(f"Error: the level must be from 1 to {MAX_LEVEL:,}.")
        return level
    level, tier = to_int(tokens[0]), to_int(tokens[1])
    if not (1 <= level <= LEVELS_PER_TIER and 1 <= tier <= MAX_TIER):
        raise ValueError(f"Error: use a level from 1 to {LEVELS_PER_TIER} and a tier from 1 to {MAX_TIER} (e.g. 200 tier 2).")
    return absolute_level(level, tier)


def title_case(name):
    """A legend name with every word capitalized and the rest lowercase: 'mad MAGGIE' -> 'Mad Maggie'."""
    return " ".join(word.capitalize() for word in name.split())


def clean(s, w):
    s = title_case((s or "").replace("|", "/"))[:w].strip()
    return s or NO_LEGEND


def resolve_legend(name, known):
    """The known legend a typed name stands for (any case): an exact match wins, then the only legend
    starting with it. None if there is none; ValueError if several start with it."""
    name = name.lower()
    hits = sorted(leg for leg in known if leg.lower().startswith(name))
    exact = [leg for leg in hits if leg.lower() == name]
    if exact:
        return exact[0]
    if len(hits) > 1:
        raise ValueError(f"Error: '{name}' matches several legends ({', '.join(hits)}); type more letters.")
    return hits[0] if hits else None


def parse_legend(tokens):
    """[legend] of a match -> the legend (None if omitted). Matches take no level: a number among
    the tokens ("5 1 57", "5 1 wraith +3") is a ValueError; levels go through <n>l / accountl <n>.
    So is a quick token ("5 1 2l", "5k wraith 2l"), which would otherwise become part of a legend name."""
    if any(LVL_TOKEN_RE.match(t) for t in tokens):
        raise ValueError("Error: matches take no level; set it with <n>l or accountl <n> (e.g. 3l or accountl 700).")
    if any(QUICK_RE.match(t) for t in tokens):
        raise ValueError("Error: type <n>k, <n>w and <n>l together before the legend (e.g. 5k 1w 2l wraith).")
    return " ".join(tokens) if tokens else None


def parse_match(tokens, pinned=False):
    """A match -> (kills, wins, legend or None). Three forms:
    - '<kills>': one number alone is kills, 0 wins (e.g. '7'), or 1 win when a legend is pinned
      (the same as typing '<kills> <legend>');
    - '<kills> <wins> [legend]': two numbers are always kills and wins (no win added);
    - '<kills> <legend>': one number followed by the legend counts as 1 win (e.g. '5 wraith').
    InputError if it is none of them; ValueError (from parse_legend) for a level among the legend tokens."""
    if not tokens or not NUM_RE.match(tokens[0]):
        raise InputError()
    if len(tokens) == 1:
        return to_int(tokens[0]), int(pinned), None
    if NUM_RE.match(tokens[1]):
        return to_int(tokens[0]), to_int(tokens[1]), parse_legend(tokens[2:])
    return to_int(tokens[0]), 1, parse_legend(tokens[1:])  # "5 +3" is still rejected as a level


def parse_when(when):
    """None -> now; otherwise the session's active date, 'YYYY-MM-DD HH:MM' (checked by parse_day)."""
    return datetime.strptime(when, DFMT) if when else datetime.now()


def parse_day(s):
    try:
        return datetime.strptime(s, DAY_FMT).strftime(DAY_FMT)
    except ValueError:
        raise ValueError("Error: use 'date YYYY-MM-DD' or 'date today'.") from None
