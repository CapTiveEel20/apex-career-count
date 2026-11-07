#!/usr/bin/env python3
"""Apex Legends stats tracker on plain .txt files (standard library only).

Entry point only: the code lives in the `apex` package next to this file.

Usage:
  python apex_stats.py add <kills> <wins> [legend] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
  python apex_stats.py add <kills> <legend> [--date ...]   (a match with 1 win, e.g. add 5 wraith)
  python apex_stats.py report
  python apex_stats.py l        (base legends' all-time kills and wins + top 3 legends by kills this month)
  python apex_stats.py m
  python apex_stats.py <n> | <n>l | +<n>  [--date ...]   (set level n / add n levels)
  python apex_stats.py <n>k | <n>w [legend] [--date ...]   (n kills only / n wins only, optional legend)
  python apex_stats.py lv       (level report)
  python apex_stats.py k | w    (kills / wins per legend)
  python apex_stats.py log      (this month's matches; account and base updates excluded)
  python apex_stats.py logl     (level history: this month's level updates + earlier days)
  python apex_stats.py undo     (remove the last entry, base or account change)
  python apex_stats.py account [<kills> <wins>] [--date ...]   (kills and wins only)
                                (show the global all-time account totals; the first time, save them;
                                 afterwards, log the gain (new - saved) as an entry with no legend;
                                 lower totals are an error and change nothing;
                                 every ACCOUNT line shows the current level)
  python apex_stats.py base [<legend> <kills> <wins>] [--date ...]
                                (list the bases; the first time, set a legend's all-time totals;
                                 afterwards, log the gain (new - current) as a match for it)
  python apex_stats.py c        (quick-start cheat sheet)
  python apex_stats.py          (interactive mode: "<kills> <wins> [legend]", "<kills> <legend>", <n>, <n>l,
                                 <n>k, <n>w, account [<kills> <wins>], base <legend> <kills> <wins>,
                                 report, m, l, lv, k, w, log, logl, undo, c, date YYYY-MM-DD |
                                 date today, p (sticky legend ON/OFF), - (unpin it, sticky OFF);
                                 an empty line quits)
  Sticky legend (interactive mode): OFF by default; "p" turns it ON/OFF. While ON, a typed legend
  is pinned and reused by later matches and <n>k / <n>w that omit it; typing another legend
  replaces it; "-" unpins it and turns sticky OFF. account and level updates never use it.
  Every match adds its kills/wins to its legend's all-time totals (base + logged) and to the
  global account totals.
  Terminal numbers use thousands separators (15,000); kills/wins input may use them too.
  Global option: --dir <folder>  (default: ./apex_data next to the script)

Matches take no level: everything after kills and wins is the legend, and a number there is
rejected. "<kills> <legend>" (one number, then a legend) is a match with 1 win; with two numbers
they are always kills and wins. Levels are their own entries: "700" = absolute level (rejected if lower than the last
recorded level), "3l" or "+3" = last recorded level + 3. SAVED lines of matches show the current
account level.

"level" is the account level reached (0 = not recorded). It can never go down: a new level
must be >= the last level recorded before its date and <= the next level recorded after it.
"+<n>" records (last level recorded before the entry's date) + n.

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
