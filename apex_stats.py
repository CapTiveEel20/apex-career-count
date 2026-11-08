#!/usr/bin/env python3
"""Apex Legends stats tracker on plain .txt files (standard library only).

Entry point only: the code lives in the `apex` package next to this file.

Usage:
  python apex_stats.py add <kills> <wins> [legend] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
  python apex_stats.py add <kills> <legend> [--date ...]   (a match with 1 win, e.g. add 5 wraith)
  python apex_stats.py report
  python apex_stats.py l        (base legends' all-time kills and wins + top 3 legends by kills this month)
  python apex_stats.py m
  python apex_stats.py <kills> [wins] [legend]   (same as add; a number alone = 0 wins)
  python apex_stats.py <n>l [--date ...]   (add n levels)
  python apex_stats.py accountl <n> [--date ...]   (set the absolute level; lower asks y/n)
  python apex_stats.py <n>k | <n>w [legend] [--date ...]   (n kills only / n wins only, optional legend)
  python apex_stats.py k | w    (kills / wins per legend)
  python apex_stats.py log      (recent matches and recent levels, side by side)
  python apex_stats.py undo     (remove the last entry, base or account change)
  python apex_stats.py account [<kills> <wins> [level]] [--date ...]
                                (show the global all-time account totals; the first time, save them;
                                 afterwards, log the gain (new - saved) as an entry with no legend;
                                 lower totals ask y/n, then replace the saved ones, nothing logged;
                                 every ACCOUNT line shows the current level)
  python apex_stats.py base [<legend> <kills> <wins>] [--date ...]
                                (list the bases; the first time, set a legend's all-time totals;
                                 afterwards, log the gain (new - current) as a match for it;
                                 lower values, or 0 0 to remove it, ask y/n)
  python apex_stats.py help     (what each command does)
  python apex_stats.py          (interactive mode: "<kills> [wins] [legend]", "<kills> <legend>", <n>l,
                                 <n>k, <n>w, account [<kills> <wins> [level]], accountl <n>, base <legend> <kills> <wins>,
                                 report, m, l, k, w, log, undo, help, date YYYY-MM-DD |
                                 date today, p <name> (lock the sticky legend), - (clear it, sticky OFF);
                                 an empty line quits)
  Sticky legend (interactive mode): OFF by default; "p <name>" locks a legend set with base. It is
  reused by later matches and <n>k / <n>w that omit a legend; a legend typed in an entry is used
  once; "-" clears it and turns sticky OFF. account and level updates never use it.
  Every match adds its kills/wins to its legend's all-time totals (base + logged) and to the
  global account totals.
  Terminal numbers use thousands separators (15,000); kills/wins input may use them too.
  Global option: --dir <folder>  (default: ./apex_data next to the script)

Matches take no level: everything after kills and wins is the legend, and a number there is
rejected. A number alone is kills with 0 wins; "<kills> <legend>" (one number, then a legend) is a
match with 1 win; with two numbers they are always kills and wins. Levels are their own entries:
"accountl 700" = absolute level, "3l" = last recorded level + 3. SAVED lines of matches show the
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
  @LV    highest level reached per day (previous months, last year + 1 baseline)
  @BU    base and @ACCOUNT changes of this month (id, date, target, old value), so undo reverts them
  L      one log entry (date, legend, kills, wins, level, id, acc, src = M/A/B/L origin)
  #      headers/comments (ignored by the parser)
  Summaries after "# SUMMARY" are recomputed on every write and never parsed.
"""
from apex.cli import main

if __name__ == "__main__":
    main()
