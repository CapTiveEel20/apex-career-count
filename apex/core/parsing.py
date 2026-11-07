"""User-input parsing: number/level/quick tokens, legend names, the [legend] of a match, dates."""
import re
from datetime import datetime

from apex.config import DAY_FMT, DFMT, NO_LEGEND

NUM_RE = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)$")  # kills/wins: "15000" or "15,000"
QUICK_RE = re.compile(r"^\+?(\d+)([kwl])$", re.IGNORECASE)  # quick-add: "5k" kills only, "1w" wins only, "3l" +3 levels
LEVEL_RE = re.compile(r"^\+?\d+$")  # level-only input: "700" (absolute) or "+5" (relative)
LVL_TOKEN_RE = re.compile(r"^[+-]?\d+$")  # a number where a legend is expected ("57", "+3", "-5"): rejected


class InputError(ValueError):
    """Unrecognized command or malformed input: the REPL answers with QUICK_GUIDE."""


def is_quick(token):
    """A single-token entry: a level ("700", "+3") or a quick entry ("3l", "5k", "1w")."""
    return bool(LEVEL_RE.match(token) or QUICK_RE.match(token))


def parse_quick(tokens):
    """A single-token entry -> (token, legend or None); None if tokens are not one. Only <n>k / <n>w
    take an optional legend after them ("5k wraith"); levels ("700", "3l", "+3") never take one.
    ValueError (from parse_legend) for a number among the legend tokens."""
    head = tokens[0]
    if len(tokens) == 1:
        return (head, None) if is_quick(head) else None
    m = QUICK_RE.match(head)
    if m and m.group(2).lower() in "kw":
        return head, parse_legend(tokens[1:])
    return None


def to_int(s):
    """Whole number from user input, with or without thousands separators ("15,000")."""
    return int(s.replace(",", ""))


def clean(s, w):
    s = (s or "").replace("|", "/").strip().capitalize()[:w]
    return s or NO_LEGEND


def parse_legend(tokens):
    """[legend] of a match -> the legend (None if omitted). Matches take no level: a number among
    the tokens ("5 1 57", "5 1 wraith +3") is a ValueError; levels go through <n> / <n>l."""
    if any(LVL_TOKEN_RE.match(t) for t in tokens):
        raise ValueError("Error: matches take no level; set it with <n> or <n>l (e.g. 700 or 3l).")
    return " ".join(tokens) if tokens else None


def parse_match(tokens):
    """A match -> (kills, wins, legend or None). Two forms:
    - '<kills> <wins> [legend]': two numbers are always kills and wins (no win added);
    - '<kills> <legend>': one number followed by the legend counts as 1 win (e.g. '5 wraith').
    InputError if it is neither; ValueError (from parse_legend) for a level among the legend tokens."""
    if len(tokens) < 2 or not NUM_RE.match(tokens[0]):
        raise InputError()
    if NUM_RE.match(tokens[1]):
        return to_int(tokens[0]), to_int(tokens[1]), parse_legend(tokens[2:])
    return to_int(tokens[0]), 1, parse_legend(tokens[1:])  # "5 +3" is still rejected as a level


def parse_when(when):
    """None -> now; 'YYYY-MM-DD HH:MM' exact; 'YYYY-MM-DD' -> that day at the current time."""
    if not when:
        return datetime.now()
    when = when.strip()
    for fmt in (DFMT, DAY_FMT):
        try:
            dt = datetime.strptime(when, fmt)
        except ValueError:
            continue
        if fmt == DAY_FMT:
            now = datetime.now()
            dt = dt.replace(hour=now.hour, minute=now.minute)
        return dt
    raise ValueError("Error: date must be 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'.")


def parse_day(s):
    try:
        return datetime.strptime(s, DAY_FMT).strftime(DAY_FMT)
    except ValueError:
        raise ValueError("Error: use 'date YYYY-MM-DD' or 'date today'.") from None
