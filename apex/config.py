"""Constants shared by every layer: file names and tags, date formats, column widths, aggregates."""
import os
import re
import sys

# Next to apex_career_diary.py (the parent of this package), or next to the executable when frozen
# (PyInstaller unpacks the package into a temp dir)
if getattr(sys, "frozen", False):
    _ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(_ROOT, "apex_data")
SEMI_MONTHS = 6
YEAR_MONTHS = 12
LV_KEEP_DAYS = 366
FNAME = "apex_stats_{}.txt"
FRE = re.compile(r"^apex_stats_(\d{4}-\d{2})\.txt$")
FOOTER_MARK = "# SUMMARY"
NO_LEGEND = "-"
DFMT = "%Y-%m-%d %H:%M"
DAY_FMT = "%Y-%m-%d"
MONTH_FMT = "%Y-%m"
ACCOUNT_FILE = "account_stats.txt"  # global all-time account totals (never rotated)
ACC_TAG = "@ACCOUNT"
BASE_TAG = "@BASE"  # per-legend base: all-time totals minus the logged entries (same file)

# Aggregates: LOGS, KILLS, WINS
AGG = (("LOGS", 6), ("KILLS", 8), ("WINS", 8))  # stored in header lines (LOGS kept for file-format compatibility)
REP = AGG[1:]  # columns shown in report tables: KILLS, WINS (no LOGS)
NA = len(AGG)
TAG_W, REF_W, LEG_W = 7, 13, 12
# Log record: (date, legend, kills, wins, level, id, acc, src)  acc = 1 if added to the account totals
# src = where the entry came from (SRC column): a match, an account update, a base update or a level update
SRC_MATCH, SRC_ACCOUNT, SRC_BASE, SRC_LEVEL = "M", "A", "B", "L"
# The part of a base gain that an account gain of the same month already added: it counts for its legend
# only, never again for the account totals or 'report' (see aggregates.unclaimed)
SRC_CLAIM = "C"
# Hidden command aliases (alias -> command), accepted by the REPL but never shown in any help, menu
# or document
ALIASES = {"duno": "undo"}
TOP_MATCHES = 5  # size of the all-time highest-kill matches leaderboard (@TK header)
TOP_GAMES = 10  # size of the current month's best games ('g', left table)
TOP_MONTH_BESTS = 6  # size of the all-time monthly bests ('g', right table)
ABORTED = "Aborted: nothing changed."  # a lowering of account, base or level was not confirmed
UI_WIDTH = 79  # width of the main menu; prompts line up with its left edge
LEVELS_PER_TIER, MAX_TIER = 500, 4  # account levels are shown as level + tier and stored as absolute
MAX_LEVEL = LEVELS_PER_TIER * MAX_TIER
