"""Interactive mode: one entry or command per line, sticky legend, active date; empty line quits.

Session.handle(line) runs one line and returns the text to print, so interactive() is only the
input/print loop and every rule can be exercised without a terminal.
"""
from datetime import datetime

from apex.config import ALIASES, DAY_FMT, DEFAULT_DIR, LEG_W, NO_LEGEND
from apex.core.parsing import InputError, clean, parse_day, parse_match, parse_quick
from apex.display.colors import paint, setup
from apex.display.messages import fmt_saved, fmt_totals
from apex.services.account import account_cmd, accountl_cmd
from apex.services.bases import base_cmd
from apex.services.entries import save_match, save_quick, undo
from apex.storage.account_file import load_acct
from apex.ui.menus import help_text, quick_guide
from apex.ui.reports import VIEWS, legend_text


def _ask(prompt):
    """A y/n question: only 'y' proceeds (end of input or Ctrl+C = no)."""
    try:
        return input(prompt).strip() == "y"
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def confirm_lower():
    """Ask before an absolute value goes down."""
    return _ask("Warning: New value is lower than current. Proceed? (y/n): ")


def confirm_new_legend(name):
    """Ask before a match creates a legend nobody knows yet."""
    return _ask(f"Unknown legend '{name}'. Create new? (y/n): ")


class Sticky:
    """Sticky legend: OFF by default. 'p <legend>' locks a legend set with 'base'; it is then reused
    by matches without a legend and by <n>k / <n>w, until '-' clears it."""

    def __init__(self):
        self.legend = None

    def pin(self, legend):
        self.legend = legend
        return f"  Sticky legend ON: {legend} is locked."

    def clear(self):
        self.legend = None
        return "  Sticky legend cleared and OFF: entries without a legend are saved with no legend."

    def typed(self, legend):
        """A match was saved with this typed legend: "-" clears the lock; any other leaves it as is."""
        if legend == NO_LEGEND:
            self.clear()

    @property
    def tag(self):
        """Prompt tag: the locked legend, None when OFF."""
        return self.legend


class Session:
    """One interactive session: data folder, active date (None = system date) and sticky legend."""

    def __init__(self, d, confirm=confirm_lower, confirm_legend=confirm_new_legend):
        self.d, self.day, self.sticky, self.confirm = d, None, Sticky(), confirm
        self.confirm_legend = confirm_legend

    @property
    def prompt(self):
        tags = [t for t in (self.day, self.sticky.tag) if t]
        return f"[{' | '.join(tags)}]> " if tags else "> "

    def handle(self, line):
        """Run one non-empty input line; returns the text to print. Unrecognized or malformed input
        answers with the quick guide, a broken rule with its error message; a data file that cannot
        be read (locked, no permission) with an error, and the session goes on."""
        try:
            return self._run(line.strip())
        except InputError:
            return quick_guide()
        except ValueError as e:
            return paint(str(e)) + "\n"
        except OSError as e:
            return f"Error: could not read the data files ({e}).\n"

    def _run(self, line):
        parts = line.split()
        cmd = ALIASES.get(line.lower(), line.lower())
        head = parts[0].lower()
        if head == "ls":  # ls <name>: search the base legends
            if len(parts) < 2:
                raise InputError()
            return legend_text(self.d, search=" ".join(parts[1:]))
        if cmd in VIEWS:
            return VIEWS[cmd](self.d)
        if cmd == "undo":
            return undo(self.d)
        if cmd == "help":
            return help_text()
        if head == "date":
            return self._set_date(parts)
        if head == "p":
            return self._pin(parts[1:]) + "\n"
        if cmd == NO_LEGEND:  # "-" alone: unpin the legend and turn sticky OFF, nothing is saved
            return self.sticky.clear() + "\n"
        when = f"{self.day} {datetime.now():%H:%M}" if self.day else None
        if head == "base":
            return base_cmd(self.d, parts[1:], when, self.confirm)
        if head == "account":  # kills and wins only, never the sticky legend
            return account_cmd(self.d, parts[1:], when, self.confirm)
        if head == "accountl":
            return accountl_cmd(self.d, parts[1:], when, self.confirm)
        quick = parse_quick(parts)
        if quick:  # 3l (never a legend); 5k, 1w [legend] (typed legend, else the pinned one)
            token, typed = quick
            legend = typed if typed is not None else self.sticky.legend
            saved = save_quick(self.d, token, when, legend, self.confirm_legend)
        else:  # anything else must be a match: <kills>, <kills> <wins> [legend] or <kills> <legend> (1 win)
            kills, wins, typed = parse_match(parts, pinned=self.sticky.legend is not None)
            legend = typed if typed is not None else self.sticky.legend
            saved = save_match(self.d, kills, wins, legend, when, self.confirm_legend)
        if typed is not None:  # a typed "-" unlocks the sticky legend; any other leaves it as is
            self.sticky.typed(saved.entry.legend)
        return fmt_saved(saved.entry, saved.level) + "\n" + fmt_totals(saved.totals)

    def _pin(self, name):
        """p <legend>: lock a legend set with 'base'; a missing or unknown name changes nothing."""
        legend = clean(" ".join(name), LEG_W)
        if legend not in load_acct(self.d).bases:
            raise ValueError("Invalid or missing legend name. Use: p <name>")
        return self.sticky.pin(legend)

    def _set_date(self, parts):
        if len(parts) != 2:
            raise InputError()
        try:
            day = None if parts[1].lower() == "today" else parse_day(parts[1])
        except ValueError:
            raise InputError() from None
        if day and day > datetime.now().strftime(DAY_FMT):  # a future month would close the current one
            raise ValueError(f"Error: {day} is in the future; the active date did not change.")
        self.day = day
        return f"  Active date: {self.day or 'today (system)'}\n"


def interactive(d=DEFAULT_DIR):
    setup()
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
