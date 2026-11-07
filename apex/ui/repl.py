"""Interactive mode: one entry or command per line, sticky legend, active date; empty line quits."""
from datetime import datetime

from apex.config import NO_LEGEND
from apex.core.parsing import LEVEL_RE, NUM_RE, QUICK_RE, InputError, parse_day, parse_extra, to_int
from apex.display.colors import paint
from apex.display.messages import fmt_saved
from apex.services.account import account_cmd
from apex.services.bases import base_cmd
from apex.services.entries import save_log, save_quick, undo
from apex.ui.menus import cheat_text, quick_guide
from apex.ui.reports import VIEWS


def interactive(d):
    print(quick_guide(), end="")
    day = None  # None = system date
    sticky = None  # sticky legend: last legend typed, reused by matches and account entries that omit it
    while True:
        tags = [t for t in (day, sticky) if t]
        try:
            line = input(f"[{' | '.join(tags)}]> " if tags else "> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd = line.lower()
        if not cmd:  # only an empty line quits
            break
        parts = line.split()
        head = parts[0].lower()
        try:
            if cmd in VIEWS:
                print(VIEWS[cmd](d), end="")
                continue
            if cmd == "undo":
                print(undo(d), end="")
                continue
            if cmd == "c":
                print(cheat_text(cli=False), end="")
                continue
            if head == "date":
                if len(parts) != 2:
                    raise InputError()
                try:
                    day = None if parts[1].lower() == "today" else parse_day(parts[1])
                except ValueError:
                    raise InputError() from None
                print(f"  Active date: {day or 'today (system)'}")
                continue
            when = f"{day} {datetime.now():%H:%M}" if day else None
            if head == "base":  # list / first time: set a legend's all-time totals / later: log the gain
                print(base_cmd(d, parts[1:], when), end="")
                continue
            if head == "account":  # show / first set / log the gain (new - saved) as a match
                text, rec, typed = account_cmd(d, parts[1:], when, sticky)
                print(text, end="")
                if rec and typed is not None:
                    sticky = rec[1] if rec[1] != NO_LEGEND else None
                continue
            if len(parts) == 1 and (LEVEL_RE.match(parts[0]) or QUICK_RE.match(parts[0])):
                _, _, _, rec = save_quick(d, parts[0], when)  # 700, 3l, +3, 5k, 1w (never a legend)
            else:  # anything else must be a match: <kills> <wins> [legend] [level]
                if len(parts) < 2 or not (NUM_RE.match(parts[0]) and NUM_RE.match(parts[1])):
                    raise InputError()
                try:
                    typed, level, delta = parse_extra(parts[2:])
                except ValueError:
                    raise InputError() from None
                legend = typed if typed is not None else sticky
                _, _, _, rec = save_log(d, to_int(parts[0]), to_int(parts[1]), legend, when, level, delta)
                if typed is not None:  # a typed legend replaces the sticky one ("-" clears it)
                    sticky = rec[1] if rec[1] != NO_LEGEND else None
        except InputError:
            print(quick_guide(), end="")
            continue
        except ValueError as e:
            print(paint(str(e)))
            continue
        print(fmt_saved(rec))
