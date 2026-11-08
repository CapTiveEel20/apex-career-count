"""Command line: argparse sub-commands, quick single-token entries, and the default data folder."""
import argparse
import os
import sys

from apex.config import ALIASES
from apex.core.parsing import NUM_RE, InputError, is_quick, parse_match, parse_quick
from apex.display import colors
from apex.display.colors import paint
from apex.display.messages import fmt_saved, fmt_totals
from apex.services.account import account_cmd, accountl_cmd
from apex.services.bases import base_cmd
from apex.services.entries import save_log, save_quick, undo
from apex.ui.menus import quick_guide
from apex.ui.reports import VIEWS, legend_text
from apex.ui.repl import confirm_lower, interactive

USAGE_ADD = ('python apex_stats.py [add] <kills> [wins] [legend] | <kills> <legend> [--l NAME] '
             '[--date "YYYY-MM-DD[ HH:MM]"]'
             '   # <kills> alone = 0 wins; <kills> <legend> = 1 win; legend defaults to "-"; '
             "matches take no level (use <n>l / accountl <n>)")
USAGE_NUM = ('python apex_stats.py <n>l | <n>k [legend] | <n>w [legend] [--date "YYYY-MM-DD[ HH:MM]"]'
             "   # <n>l = n more levels, <n>k / <n>w = n kills / n wins only")
USAGE_ACCOUNTL = ('python apex_stats.py accountl <n> [--date "YYYY-MM-DD[ HH:MM]"]'
                  "   # set the absolute account level (asks y/n if lower than the current one)")
USAGE_REPORT = "python apex_stats.py report   # match summaries, followed by the level report (same as lv)"
USAGE_L = ("python apex_stats.py l | lw | la | lm | ls <name>   # base legends' all-time kills and wins by kills "
           "(l), wins (lw), name (la) or last match (lm), or searched by name (ls), next to the top 3 legends by "
           "kills this month")
USAGE_K = "python apex_stats.py k   # kills per legend: month, semiannual, annual, all-time + GRAND TOTAL"
USAGE_W = "python apex_stats.py w   # wins per legend: month, semiannual, annual, all-time + GRAND TOTAL"
USAGE_M = "python apex_stats.py m   # kills and wins of the current file + top 5 all-time highest-kill matches"
USAGE_LV = "python apex_stats.py lv   # levels gained over 1 week, 1/3/6 months and 1 year"
USAGE_UNDO = ("python apex_stats.py undo   # remove the most recently added entry, base or account change "
              "(repeat to go further back)")
USAGE_ACCOUNT = ('python apex_stats.py account [<kills> <wins> [level]] [--date "YYYY-MM-DD[ HH:MM]"]'
                 "   # show the totals; 1st time: save them; then: log the gain (new - saved), no legend; "
                 "level = also set the account level; lower values ask y/n")
USAGE_LOG = "python apex_stats.py log   # this month's match entries (account and base updates excluded)"
USAGE_LOGL = "python apex_stats.py logl   # level history: this month's level updates + earlier days"
USAGE_BASE = ('python apex_stats.py base [<legend> <kills> <wins>] [--date "YYYY-MM-DD[ HH:MM]"]'
              "   # list; 1st time: set a legend's all-time totals; then: log the gain (0 0 removes); "
              "lower values ask y/n")
USAGE_DIR = "python apex_stats.py --dir <path> ...   # data folder; default is ./apex_data next to the script"
USAGE_REPL = ("python apex_stats.py   # interactive mode: '<kills> [wins] [legend]', '<kills> <legend>', "
              "'<n>l', "
              "'<n>k', '<n>w' per line, account/accountl/base, report/m/l/lw/la/lm/ls/lv/k/w/log/logl/undo/c, "
              "'date YYYY-MM-DD' / 'date today', sticky legend, empty line to quit")
USAGE_C = "python apex_stats.py c   # help menu"
USAGE = "\n  " + "\n  ".join((USAGE_ADD, USAGE_NUM, USAGE_REPORT, USAGE_M, USAGE_L, USAGE_LV, USAGE_K, USAGE_W,
                              USAGE_LOG, USAGE_LOGL, USAGE_UNDO, USAGE_ACCOUNT, USAGE_ACCOUNTL, USAGE_BASE, USAGE_C,
                              USAGE_DIR, USAGE_REPL))
# Next to apex_stats.py (the parent of this package), or next to the executable when frozen
# (PyInstaller unpacks the package into a temp dir)
if getattr(sys, "frozen", False):
    _ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(_ROOT, "apex_data")


def cmd_add(a):
    try:
        vals = list(a.values)
        if len(vals) == 1 and a.legend:  # add <kills> --l NAME = <kills> <legend> (1 win)
            vals.append(a.legend)
        try:
            kills, wins, legend = parse_match(vals)
        except InputError:
            raise ValueError("Format: add <kills> [wins] [legend]   or   add <kills> <legend> (1 win)   "
                             "(levels: python apex_stats.py 3l  or  accountl 700)") from None
        if a.legend:
            legend = a.legend
        _, shown, level, rec, totals = save_log(a.dir, kills, wins, legend, a.date)
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(fmt_saved(rec, level) + "\n" + fmt_totals(totals))
    print(shown, end="")


def cmd_level(argv):
    """python apex_stats.py [--dir PATH] <n>l | <n>k | <n>w [--date ...]"""
    lp = argparse.ArgumentParser(prog="apex_stats.py", usage="\n  " + USAGE_NUM)
    lp.add_argument("value", metavar="<n>l | <n>k | <n>w")
    lp.add_argument("legend", nargs="*", metavar="[legend]", help="legend of <n>k / <n>w (levels take none)")
    lp.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"')
    lp.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR)
    a = lp.parse_args(argv)
    try:
        quick = parse_quick([a.value] + a.legend)
        if not quick:
            raise ValueError("Error: levels take no legend; only <n>k / <n>w do (e.g. 5k wraith).")
        token, legend = quick
        _, _, level, rec, totals = save_quick(a.dir, token, a.date, legend)
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(fmt_saved(rec, level) + "\n" + fmt_totals(totals), end="")


def cmd_view(a):
    try:
        print(VIEWS[a.cmd](a.dir), end="")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_ls(a):
    try:
        print(legend_text(a.dir, search=" ".join(a.name)), end="")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_account(a):
    try:
        text = account_cmd(a.dir, a.values, a.date, confirm_lower)
    except InputError:
        sys.exit("Format: account   or   account <kills> <wins> [level]   (e.g. account 12000 450 or account 12000 450 700)")
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(text, end="")


def cmd_accountl(a):
    try:
        text = accountl_cmd(a.dir, [a.value], a.date, confirm_lower)
    except InputError:
        sys.exit("Format: accountl <n>   (absolute account level, e.g. accountl 700)")
    except ValueError as e:
        sys.exit(paint(str(e)))
    print(text, end="")


def cmd_base(a):
    try:
        print(base_cmd(a.dir, a.values, a.date, confirm_lower), end="")
    except InputError:
        sys.exit("Format: base   or   base <legend> <kills> <wins>   (e.g. base wraith 3000 120)")
    except ValueError as e:
        sys.exit(paint(str(e)))


def cmd_c(_a):
    print(quick_guide(), end="")


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
    i = 2 if argv[0] == "--dir" and len(argv) > 2 else 0
    argv[i] = ALIASES.get(argv[i], argv[i])  # hidden aliases: never listed in any usage, help or menu text
    if NUM_RE.match(argv[i]):  # "7", "7 1", "7 1 wraith": a match
        argv.insert(i, "add")
    if is_quick(argv[i]):  # "3l", "5k", "1w"
        cmd_level(argv)
        return
    ap = argparse.ArgumentParser(usage=USAGE, description="Apex Legends stats tracker on .txt files")
    ap.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR,
                    help="data folder (default: ./apex_data next to the script)")
    sp = ap.add_subparsers(dest="cmd", required=True,
                           metavar="{add,report,m,l,lw,la,lm,ls,lv,k,w,log,logl,undo,account,accountl,base,c}")
    p = sp.add_parser("add", prog="apex_stats.py add", usage="\n  " + USAGE_ADD,
                      help="record a match (kills, wins, legend)")
    p.add_argument("values", nargs="+", metavar="<kills> [wins] [legend] | <kills> <legend>",
                   help="kills, wins, then an optional legend; kills alone (= 0 wins); or kills and a legend (= 1 win). "
                        "No level: use <n>l / accountl <n>")
    p.add_argument("--l", dest="legend", metavar="NAME", help='legend (default: "-")')
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the entry (default: now)")
    p.set_defaults(fn=cmd_add)
    for name, usage, hlp in (("report", USAGE_REPORT, "match summaries + level report"),
                             ("m", USAGE_M, "kills and wins of the current file + top 5 matches"),
                             ("l", USAGE_L, "base legends (all-time) by kills + top 3 by kills this month"),
                             ("lw", USAGE_L, "same as l, sorted by wins"),
                             ("la", USAGE_L, "same as l, sorted by name"),
                             ("lm", USAGE_L, "same as l, sorted by last match (most recent first)"),
                             ("lv", USAGE_LV, "levels gained (report only)"),
                             ("k", USAGE_K, "kills per legend (month, semiannual, annual, all-time)"),
                             ("w", USAGE_W, "wins per legend (month, semiannual, annual, all-time)"),
                             ("log", USAGE_LOG, "this month's matches (no account/base updates)"),
                             ("logl", USAGE_LOGL, "level history (this month + earlier days)")):
        sp.add_parser(name, prog=f"apex_stats.py {name}", usage="\n  " + usage,
                      help=hlp).set_defaults(fn=cmd_view)
    p = sp.add_parser("ls", prog="apex_stats.py ls", usage="\n  " + USAGE_L,
                      help="same as l, only the base legends whose name contains <name>")
    p.add_argument("name", nargs="+", metavar="<name>", help="part of the legend name (any case)")
    p.set_defaults(fn=cmd_ls)
    sp.add_parser("undo", prog="apex_stats.py undo", usage="\n  " + USAGE_UNDO,
                  help="remove the most recent entry, base or account change").set_defaults(fn=cmd_undo)
    p = sp.add_parser("account", prog="apex_stats.py account", usage="\n  " + USAGE_ACCOUNT,
                      help="show / set the global account totals, or log the gain from new totals")
    p.add_argument("values", nargs="*", metavar="<kills> <wins> [level]",
                   help="new all-time account kills and wins, optionally the account level (omit to show them)")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the logged gain (default: now)")
    p.set_defaults(fn=cmd_account)
    p = sp.add_parser("accountl", prog="apex_stats.py accountl", usage="\n  " + USAGE_ACCOUNTL,
                      help="set the absolute account level")
    p.add_argument("value", metavar="<n>", help="new absolute account level")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the level (default: now)")
    p.set_defaults(fn=cmd_accountl)
    p = sp.add_parser("base", prog="apex_stats.py base", usage="\n  " + USAGE_BASE,
                      help="list the bases / set a legend's all-time totals, or log the gain")
    p.add_argument("values", nargs="*", metavar="<legend> <kills> <wins>",
                   help="legend and its all-time kills and wins (omit to list them)")
    p.add_argument("--date", metavar='"YYYY-MM-DD[ HH:MM]"', help="date of the logged gain (default: now)")
    p.set_defaults(fn=cmd_base)
    sp.add_parser("c", prog="apex_stats.py c", usage="\n  " + USAGE_C,
                  help="help menu").set_defaults(fn=cmd_c)
    a = ap.parse_args(argv)
    a.fn(a)
