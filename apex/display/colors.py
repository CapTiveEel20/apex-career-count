"""Raw ANSI colors (no external libraries): kills red, wins green, levels orange.

COLOR is module state set once by setup(). Read it only inside this module (red, green, orange,
paint, color_quick); never copy it with `from apex.display.colors import COLOR`.
"""
import os
import re
import sys

RED, GREEN, ORANGE, RESET = "\033[91m", "\033[92m", "\033[38;5;208m", "\033[0m"
COLOR = False
KW_RE = re.compile(r"[<\[]?\b(?:(kills?)|(wins?))\b[>\]]?(?:\s+\d(?:[\d,]*\d)?)?", re.IGNORECASE)
LAST_LEVEL_RE = re.compile(r"(?<=last recorded level \()\d[\d,]*(?=\))")  # (Y) of the check_level error
QUICK_TXT_RE = re.compile(r"(?<![\w+<])\+?(?:<n>|\d+)([kw])\b")  # <n>k / 5k (red), <n>w / 1w (green)
ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def init_color():
    """Colors only on a real terminal, unless NO_COLOR is set. On Windows, turn on the
    console's ANSI (virtual terminal) mode with ctypes from the standard library."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            if not k32.GetConsoleMode(h, ctypes.byref(mode)):
                return False
            k32.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        except (AttributeError, OSError):
            return False
    return True


def setup():
    """Enable colors for this run if the terminal supports them (called once by cli.main)."""
    global COLOR
    COLOR = init_color()


def _on(color):
    return COLOR if color is None else color


def red(s, color=None):
    return f"{RED}{s}{RESET}" if _on(color) else str(s)


def green(s, color=None):
    return f"{GREEN}{s}{RESET}" if _on(color) else str(s)


def orange(s, color=None):
    return f"{ORANGE}{s}{RESET}" if _on(color) else str(s)


def paint(text, color=None):
    """Color kill words (kills, <kills>, KILLS 12) red and win words (wins, [wins], WINS 3) green.
    Level words stay plain; only the (Y) of "lower than the last recorded level (Y)" turns orange.
    Used for prose and table headers; table values are colored cell by cell."""
    if not _on(color):
        return text
    text = KW_RE.sub(lambda m: red(m.group(0), True) if m.group(1) else green(m.group(0), True), text)
    return LAST_LEVEL_RE.sub(lambda m: orange(m.group(0), True), text)


def visible_len(s):
    """Length of s as shown on the terminal (ANSI color codes take no space)."""
    return len(ANSI_RE.sub("", s))


def color_quick(text):
    """Quick-add shortcuts (<n>k red, <n>w green) in menu text (paint does not match them)."""
    if not COLOR:
        return text
    return QUICK_TXT_RE.sub(lambda m: red(m.group(0)) if m.group(1) == "k" else green(m.group(0)), text)
