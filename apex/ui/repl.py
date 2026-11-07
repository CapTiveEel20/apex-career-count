"""Interactive mode: one entry or command per line, sticky legend, active date; empty line quits."""
from datetime import datetime

from apex.config import NO_LEGEND
from apex.core.parsing import LEVEL_RE, QUICK_RE, InputError, parse_day, parse_match
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
    pin = False  # sticky legend mode, OFF by default; 'p' toggles it, '-' turns it OFF
    sticky = None  # pinned legend (mode ON only): reused by matches without a legend and by <n>k / <n>w
    while True:
        tags = [t for t in (day, sticky or ("sticky ON" if pin else None)) if t]
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
            if cmd in ("undo", "duno"):  # duno: hidden alias of undo (not shown in any menu)
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
            if cmd == "p":  # toggle sticky legend mode; turning it OFF also unpins the legend
                pin, sticky = not pin, None
                print("  Sticky legend ON: the next legend you type is pinned." if pin else
                      "  Sticky legend OFF: entries without a legend are saved with no legend.")
                continue
            if cmd == NO_LEGEND:  # "-" alone: unpin the legend and turn the mode OFF, nothing is saved
                pin, sticky = False, None
                print("  Sticky legend cleared and OFF: entries without a legend are saved with no legend.")
                continue
            when = f"{day} {datetime.now():%H:%M}" if day else None
            if head == "base":  # list / first time: set a legend's all-time totals / later: log the gain
                print(base_cmd(d, parts[1:], when), end="")
                continue
            if head == "account":  # kills and wins only: show / first set / log the gain (no legend)
                print(account_cmd(d, parts[1:], when), end="")
                continue
            if len(parts) == 1 and (LEVEL_RE.match(parts[0]) or QUICK_RE.match(parts[0])):
                # 700, 3l, +3 (never a legend); 5k, 1w take the pinned legend, if any
                _, _, level, rec = save_quick(d, parts[0], when, sticky)
            else:  # anything else must be a match: <kills> <wins> [legend] or <kills> <legend> (1 win)
                try:
                    kills, wins, typed = parse_match(parts)
                except ValueError:
                    raise InputError() from None
                legend = typed if typed is not None else sticky
                _, _, level, rec = save_log(d, kills, wins, legend, when)
                if typed is not None and rec[1] == NO_LEGEND:  # a typed "-": unpin, mode OFF
                    pin, sticky = False, None
                elif typed is not None and pin:  # mode ON: the typed legend is pinned
                    sticky = rec[1]
        except InputError:
            print(quick_guide(), end="")
            continue
        except ValueError as e:
            print(paint(str(e)))
            continue
        print(fmt_saved(rec, level))
