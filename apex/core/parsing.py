"""User-input parsing: number/level/quick tokens, legend names, the [legend] of a match, dates."""
import re
from datetime import datetime

from apex.config import DAY_FMT, DFMT, NO_LEGEND

NUM_RE = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)$")  # kills/wins: "15000" or "15,000"
QUICK_RE = re.compile(r"^\+?(\d+)([kwl])$", re.IGNORECASE)  # quick-add: "5k" kills only, "1w" wins only, "3l" +3 levels
LVL_TOKEN_RE = re.compile(r"^[+-]?\d+$")  # a number where a legend is expected ("57", "+3", "-5"): rejected


class InputError(ValueError):
    """Unrecognized command or malformed input: the REPL answers with the help menu."""


def parse_quick(tokens):
    """A quick entry -> (token, legend or None); None if tokens are not one. Only <n>k / <n>w
    take an optional legend after them ("5k wraith"); "3l" never takes one.
    ValueError for anything after "3l" and (from parse_legend) for a number among the legend tokens."""
    head = tokens[0]
    m = QUICK_RE.match(head)
    if not m:
        return None
    if len(tokens) == 1:
        return head, None
    if m.group(2).lower() == "l":
        raise ValueError("Error: <n>l takes no legend or other input (e.g. 3l).")
    return head, parse_legend(tokens[1:])


def to_int(s):
    """Whole number from user input, with or without thousands separators ("15,000")."""
    return int(s.replace(",", ""))


def clean(s, w):
    s = (s or "").replace("|", "/").strip().capitalize()[:w]
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
    the tokens ("5 1 57", "5 1 wraith +3") is a ValueError; levels go through <n>l / accountl <n>."""
    if any(LVL_TOKEN_RE.match(t) for t in tokens):
        raise ValueError("Error: matches take no level; set it with <n>l or accountl <n> (e.g. 3l or accountl 700).")
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
