"""Interactive mode: one entry or command per line, sticky legend, active date; empty line quits.

Session.handle(line) runs one line and returns the text to print, so interactive() is only the
input/print loop and every rule can be exercised without a terminal.
"""
from datetime import datetime

from apex.config import ALIASES, NO_LEGEND
from apex.core.parsing import InputError, parse_day, parse_match, parse_quick
from apex.display.colors import paint
from apex.display.messages import fmt_saved
from apex.services.account import account_cmd
from apex.services.bases import base_cmd
from apex.services.entries import save_log, save_quick, undo
from apex.ui.menus import cheat_text, quick_guide
from apex.ui.reports import VIEWS


class Sticky:
    """Sticky legend: OFF by default. While ON, the legend typed in a match is pinned and reused by
    matches without a legend and by <n>k / <n>w. Turning it OFF always unpins it."""

    def __init__(self):
        self.on, self.legend = False, None

    def toggle(self):
        self.on, self.legend = not self.on, None
        return ("  Sticky legend ON: the next legend you type is pinned." if self.on else
                "  Sticky legend OFF: entries without a legend are saved with no legend.")

    def clear(self):
        self.on, self.legend = False, None
        return "  Sticky legend cleared and OFF: entries without a legend are saved with no legend."

    def typed(self, legend):
        """A match was saved with this typed legend: "-" clears the mode; any other is pinned while ON."""
        if legend == NO_LEGEND:
            self.clear()
        elif self.on:
            self.legend = legend

    @property
    def tag(self):
        """Prompt tag: the pinned legend, 'sticky ON' with nothing pinned yet, None when OFF."""
        return self.legend or ("sticky ON" if self.on else None)


class Session:
    """One interactive session: data folder, active date (None = system date) and sticky legend."""

    def __init__(self, d):
        self.d, self.day, self.sticky = d, None, Sticky()

    @property
    def prompt(self):
        tags = [t for t in (self.day, self.sticky.tag) if t]
        return f"[{' | '.join(tags)}]> " if tags else "> "

    def handle(self, line):
        """Run one non-empty input line; returns the text to print. Unrecognized or malformed input
        answers with the quick guide, a broken rule with its error message."""
        try:
            return self._run(line.strip())
        except InputError:
            return quick_guide()
        except ValueError as e:
            return paint(str(e)) + "\n"

    def _run(self, line):
        parts = line.split()
        cmd = ALIASES.get(line.lower(), line.lower())
        head = parts[0].lower()
        if cmd in VIEWS:
            return VIEWS[cmd](self.d)
        if cmd == "undo":
            return undo(self.d)
        if cmd == "c":
            return cheat_text(cli=False)
        if head == "date":
            return self._set_date(parts)
        if cmd == "p":
            return self.sticky.toggle() + "\n"
        if cmd == NO_LEGEND:  # "-" alone: unpin the legend and turn sticky OFF, nothing is saved
            return self.sticky.clear() + "\n"
        when = f"{self.day} {datetime.now():%H:%M}" if self.day else None
        if head == "base":
            return base_cmd(self.d, parts[1:], when)
        if head == "account":  # kills and wins only, never the sticky legend
            return account_cmd(self.d, parts[1:], when)
        quick = parse_quick(parts)
        if quick:  # 700, 3l, +3 (never a legend); 5k, 1w [legend] (typed legend, else the pinned one)
            token, typed = quick
            legend = typed if typed is not None else self.sticky.legend  # a typed legend leaves sticky as is
            _, _, level, rec = save_quick(self.d, token, when, legend)
        else:  # anything else must be a match: <kills> <wins> [legend] or <kills> <legend> (1 win)
            try:
                kills, wins, typed = parse_match(parts)
            except ValueError:
                raise InputError() from None
            legend = typed if typed is not None else self.sticky.legend
            _, _, level, rec = save_log(self.d, kills, wins, legend, when)
            if typed is not None:
                self.sticky.typed(rec.legend)
        return fmt_saved(rec, level) + "\n"

    def _set_date(self, parts):
        if len(parts) != 2:
            raise InputError()
        try:
            self.day = None if parts[1].lower() == "today" else parse_day(parts[1])
        except ValueError:
            raise InputError() from None
        return f"  Active date: {self.day or 'today (system)'}\n"


def interactive(d):
    print(quick_guide(), end="")
    session = Session(d)
    while True:
        try:
            line = input(session.prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:  # only an empty line quits
            break
        print(session.handle(line), end="")
