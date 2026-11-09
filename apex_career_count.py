#!/usr/bin/env python3
"""Apex Career Diary: kills, wins and levels over time, in plain .txt files (standard library only).

Entry point only: the code lives in the `apex` package next to this file.

Usage: python apex_career_count.py   (opens the interactive menu; 'help' lists every command, an empty line quits)
  Sticky legend: OFF by default; "p <name>" locks a legend set with base. It is
  reused by later matches and <n>k / <n>w that omit a legend; a legend typed in an entry is used
  once; "-" clears it and turns sticky OFF. account and level updates never use it.
  Every match adds its kills/wins to its legend's all-time totals (base + logged) and to the
  global account totals.
  Terminal numbers use thousands separators (15,000); kills/wins input may use them too.
  Data folder: ./apex_data next to the script.

Plain-number matches take no level: everything after kills and wins is the legend, and a number
there is rejected. A number alone is kills with 0 wins (1 win with a locked legend); "<kills> <legend>"
(one number, then a legend) is a match with 1 win; with two numbers they are always kills and wins.
Levels (4 tiers of 500, stored as absolute): "accountl 700", "accountl 200 tier 2" or "accountl 200 2", "3l" = last recorded level + 3, and "<n>k [<n>w] [<n>l] [legend]"
saves kills, wins and levels as one entry (any may be omitted, in that order). SAVED lines of matches show the
current account level.

"level" is the account level reached (0 = not recorded). A new level must be <= the next level
recorded after its date; one lower than the last level recorded before its date needs a y/n
confirmation. "<n>l" records (last level recorded before the entry's date) + n.

Rotation by calendar month: one file per month (apex_stats_YYYY-MM.txt).
Global account totals (set with "account <kills> <wins>") and the per-legend bases (set with
"base <legend> <kills> <wins>") live in their own file, account_stats.txt, so they survive every
rotation; report, k and w show the account totals on top. Once set, every saved match adds its
kills/wins to them and undo subtracts them again.

Terminal output is colorized with raw ANSI codes (kills red, wins green) when stdout is a
terminal and NO_COLOR is not set. Levels are orange. Data files never contain color codes.

File format (O(1) parsing per line via a constant prefix in the first column):
  @FILE  month of the file    @HIST  all-time totals of previous months
  @PREV  per-month totals (last 11 calendar months, for semiannual/annual)
  @HL    all-time totals per legend (previous months)
  @PL    per-month, per-legend totals (last 11 months)
  @LV    last level recorded per day (previous months, last year + 1 baseline)
  @BU    base and @ACCOUNT changes of this month (id, date, target, old value), so undo reverts them
  L      one log entry (date, legend, kills, wins, level, id, acc, src = M/A/B/C/L origin)
  #      headers/comments (ignored by the parser)
  Summaries after "# SUMMARY" are recomputed on every write and never parsed.
"""
from apex.ui.repl import interactive

if __name__ == "__main__":
    interactive()
