"""User-input parsing: number/level/quick tokens, legend names, [legend] [level], dates."""
import re
from datetime import datetime

from apex.config import DAY_FMT, DFMT, NO_LEGEND

NUM_RE = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)$")  # kills/wins: "15000" or "15,000"
QUICK_RE = re.compile(r"^\+?(\d+)([kwl])$", re.IGNORECASE)  # quick-add: "5k" kills only, "1w" wins only, "3l" +3 levels
LEVEL_RE = re.compile(r"^\+?\d+$")  # level-only input: "700" (absolute) or "+5" (relative)
LVL_TOKEN_RE = re.compile(r"^[+-]?\d+$")  # [level] in a full entry: "700", "+5" (relative) or "-5" (rejected)


class InputError(ValueError):
    """Unrecognized command or malformed input: the REPL answers with QUICK_GUIDE."""


def to_int(s):
    """Whole number from user input, with or without thousands separators ("15,000")."""
    return int(s.replace(",", ""))


def clean(s, w):
    s = (s or "").replace("|", "/").strip().capitalize()[:w]
    return s or NO_LEGEND


def level_arg(token):
    """Level token -> (level, delta): "700" = absolute (700, None); "+3" = relative (0, 3)."""
    if token.startswith("+"):
        return 0, int(token)
    return int(token), None


def parse_extra(tokens):
    """[legend] [level] -> (legend, level, delta). A numeric 3rd value ("700" or "+3") is the level;
    otherwise it is the legend, and a trailing numeric value is the level. No "+" = absolute level,
    "+<n>" = last recorded level + n."""
    if not tokens:
        return None, 0, None
    if LVL_TOKEN_RE.match(tokens[0]):
        if len(tokens) > 1:
            raise ValueError("Error: nothing may follow the level.")
        return (None,) + level_arg(tokens[0])
    if len(tokens) > 1 and LVL_TOKEN_RE.match(tokens[-1]):
        return (" ".join(tokens[:-1]),) + level_arg(tokens[-1])
    return " ".join(tokens), 0, None


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
