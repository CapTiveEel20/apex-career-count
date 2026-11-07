"""Constants shared by every layer: file names and tags, date formats, column widths, aggregates."""
import re

SEMI_MONTHS = 6
YEAR_MONTHS = 12
LV_KEEP_DAYS = 366
FNAME = "apex_stats_{}.txt"
FRE = re.compile(r"^apex_stats_(\d{4}-\d{2})\.txt$")
FOOTER_MARK = "# SUMMARY"
NO_LEGEND = "-"
DFMT = "%Y-%m-%d %H:%M"
DAY_FMT = "%Y-%m-%d"
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
