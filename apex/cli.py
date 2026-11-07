"""Command line: argparse sub-commands, quick single-token entries, and the default data folder."""
import argparse
import os
import sys

from apex.core.parsing import LEVEL_RE, NUM_RE, QUICK_RE, InputError, parse_extra, to_int
from apex.display import colors
from apex.display.colors import paint
from apex.display.messages import fmt_saved
from apex.services.account import account_cmd
from apex.services.bases import base_cmd
from apex.services.entries import save_log, save_quick, undo
from apex.ui.menus import cheat_text
from apex.ui.reports import VIEWS
from apex.ui.repl import interactive

USAGE_ADD = ('python apex_stats.py add <kills> <wins> [legend] [level] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]'
             '   # numeric 3rd value = level (700 absolute, +3 relative); legend defaults to "-"')
USAGE_NUM = ('python apex_stats.py <n> | <n>l | +<n> | <n>k | <n>w [--date "YYYY-MM-DD[ HH:MM]"]'
             "   # <n> = absolute level, <n>l (or +<n>) = n more levels, <n>k / <n>w = n kills / n wins only")
USAGE_REPORT = "python apex_stats.py report   # match summaries, followed by the level report (same as lv)"
USAGE_L = "python apex_stats.py l   # all-time kills and wins per legend (base + logged entries)"
USAGE_K = "python apex_stats.py k   # kills per legend: month, semiannual, annual, all-time + GRAND TOTAL"
USAGE_W = "python apex_stats.py w   # wins per legend: month, semiannual, annual, all-time + GRAND TOTAL"
USAGE_M = "python apex_stats.py m   # total kills and wins of the current file"
USAGE_LV = "python apex_stats.py lv   # levels gained over 1 week, 1/3/6 months and 1 year"
USAGE_UNDO = "python apex_stats.py undo   # remove the most recently added entry (repeat to go further back)"
USAGE_ACCOUNT = ('python apex_stats.py account [<kills> <wins> [legend] [level]] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]'
                 "   # show the totals; 1st time: save them; then: log the gain (new - saved) as a match")
USAGE_BASE = ('python apex_stats.py base [<legend> <kills> <wins>] [--date "YYYY-MM-DD[ HH:MM]"]'
              "   # list; 1st time: set a legend's all-time totals; then: log the gain (0 0 removes)")
USAGE_DIR = "python apex_stats.py --dir <path> ...   # data folder; default is ./apex_data next to the script"
USAGE_REPL = ("python apex_stats.py   # interactive mode: '<kills> <wins> [legend] [level]', '<n>', '<n>l', "
              "'<n>k', '<n>w' per line, account/base, report/l/k/w/m/lv/undo/c, "
              "'date YYYY-MM-DD' / 'date today', sticky legend, empty line to quit")
USAGE_C = "python apex_stats.py c   # quick-start cheat sheet: all inputs and commands"
USAGE = "\n  " + "\n  ".join((USAGE_ADD, USAGE_NUM, USAGE_REPORT, USAGE_L, USAGE_K, USAGE_W, USAGE_M,
                              USAGE_LV, USAGE_UNDO, USAGE_ACCOUNT, USAGE_BASE, USAGE_C, USAGE_DIR, USAGE_REPL))
# Next to apex_stats.py (the parent of this package), or next to the executable when frozen
# (PyInstaller unpacks the package into a temp dir)
if getattr(sys, "frozen", False):
    _ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(_ROOT, "apex_data")


def cmd_add(a):
    try:
        vals = a.values
        if len(vals) < 2:
            raise ValueError("Format: add <kills> <wins> [legend] [level]   "
                             "(a level alone: python apex_stats.py 700  or  +5)")
        if not (NUM_RE.match(vals[0]) and NUM_RE.match(vals[1])):
            raise ValueError("Error: kills and wins must be whole numbers.")
        legend, level, delta = parse_extra(vals[2:])
        if a.legend:
            legend = a.legend
        _, shown, _, rec = save_log(a.dir, to_int(vals[0]), to_int(vals[1]), legend, a.date, level, delta)
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(fmt_saved(rec) + "\n")
    print(shown, end="")


def cmd_level(argv):
    """python apex_stats.py [--dir PATH] <n> | <n>l | +<n> | <n>k | <n>w [--date ...]"""
    lp = argparse.ArgumentParser(prog="apex_stats.py", usage="\n  " + USAGE_NUM)
    lp.add_argument("value", metavar="<n> | <n>l | <n>k | <n>w")
    lp.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"')
    lp.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR)
    a = lp.parse_args(argv)
    try:
        _, _, _, rec = save_quick(a.dir, a.value, a.date)
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(fmt_saved(rec))


def cmd_view(a):
    try:
        print(VIEWS[a.cmd](a.dir), end="")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_account(a):
    try:
        text, _, _ = account_cmd(a.dir, a.values, a.date, None, a.legend)
    except InputError:
        sys.exit("Format: account   or   account <kills> <wins> [legend] [level]   (e.g. account 12000 450)")
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(text, end="")


def cmd_base(a):
    try:
        print(base_cmd(a.dir, a.values, a.date), end="")
    except InputError:
        sys.exit("Format: base   or   base <legend> <kills> <wins>   (e.g. base wraith 3000 120)")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_c(_a):
    print(cheat_text(cli=True), end="")


def cmd_undo(a):
    try:
        print(undo(a.dir), end="")
    except ValueError as e:
        sys.exit(paint(str(e)))


def main():
    colors.setup()
    if len(sys.argv) == 1:
        interactive(DEFAULT_DIR)
        return
    argv = sys.argv[1:]
    first = argv[2] if argv[0] == "--dir" and len(argv) > 2 else argv[0]
    if LEVEL_RE.match(first) or QUICK_RE.match(first):  # "700", "3l", "+3", "5k", "1w"
        cmd_level(argv)
        return
    ap = argparse.ArgumentParser(usage=USAGE, description="Apex Legends stats tracker on .txt files")
    ap.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR,
                    help="data folder (default: ./apex_data next to the script)")
    sp = ap.add_subparsers(dest="cmd", required=True, metavar="{add,report,l,k,w,m,lv,undo,account,base,c}")
    p = sp.add_parser("add", prog="apex_stats.py add", usage="\n  " + USAGE_ADD,
                      help="record an entry (kills, wins, legend, level)")
    p.add_argument("values", nargs="+", metavar="<kills> <wins> [legend] [level]",
                   help="kills, wins, then legend and/or account level (numeric 3rd value = level; +<n> = relative)")
    p.add_argument("--l", dest="legend", metavar="NAME", help='legend (default: "-")')
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the entry (default: now)")
    p.set_defaults(fn=cmd_add)
    for name, usage, hlp in (("report", USAGE_REPORT, "match summaries + level report"),
                             ("l", USAGE_L, "all-time kills and wins per legend (base + logged)"),
                             ("k", USAGE_K, "kills per legend (month, semiannual, annual, all-time)"),
                             ("w", USAGE_W, "wins per legend (month, semiannual, annual, all-time)"),
                             ("m", USAGE_M, "total kills and wins of the current file"),
                             ("lv", USAGE_LV, "levels gained (report only)")):
        sp.add_parser(name, prog=f"apex_stats.py {name}", usage="\n  " + usage,
                      help=hlp).set_defaults(fn=cmd_view)
    sp.add_parser("undo", prog="apex_stats.py undo", usage="\n  " + USAGE_UNDO,
                  help="remove the most recently added entry").set_defaults(fn=cmd_undo)
    p = sp.add_parser("account", prog="apex_stats.py account", usage="\n  " + USAGE_ACCOUNT,
                      help="show / set the global account totals, or log the gain from new totals")
    p.add_argument("values", nargs="*", metavar="<kills> <wins> [legend] [level]",
                   help="new all-time account totals (omit to show them)")
    p.add_argument("--l", dest="legend", metavar="NAME", help="legend of the logged gain")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the logged gain (default: now)")
    p.set_defaults(fn=cmd_account)
    p = sp.add_parser("base", prog="apex_stats.py base", usage="\n  " + USAGE_BASE,
                      help="list the bases / set a legend's all-time totals, or log the gain")
    p.add_argument("values", nargs="*", metavar="<legend> <kills> <wins>",
                   help="legend and its all-time kills and wins (omit to list them)")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the logged gain (default: now)")
    p.set_defaults(fn=cmd_base)
    sp.add_parser("c", prog="apex_stats.py c", usage="\n  " + USAGE_C,
                  help="short quick-start cheat sheet").set_defaults(fn=cmd_c)
    a = ap.parse_args(argv)
    a.fn(a)
