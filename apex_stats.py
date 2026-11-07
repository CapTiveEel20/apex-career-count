#!/usr/bin/env python3
"""Apex Legends stats tracker on plain .txt files (standard library only).

Entry point only: the code lives in the `apex` package next to this file.

Usage:
  python apex_stats.py add <kills> <wins> [legend] [level] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
  python apex_stats.py report
  python apex_stats.py l        (all-time kills and wins per legend: base + logged entries)
  python apex_stats.py m
  python apex_stats.py <n> | <n>l | +<n>  [--date ...]   (set level n / add n levels)
  python apex_stats.py <n>k | <n>w        [--date ...]   (n kills only / n wins only, no legend)
  python apex_stats.py lv       (level report)
  python apex_stats.py k | w    (kills / wins per legend)
  python apex_stats.py undo
  python apex_stats.py account [<kills> <wins> [legend] [level]] [--l NAME] [--date ...]
                                (show the global all-time account totals; the first time, save them;
                                 afterwards, log the gain (new - saved) as a match entry)
  python apex_stats.py base [<legend> <kills> <wins>] [--date ...]
                                (list the bases; the first time, set a legend's all-time totals;
                                 afterwards, log the gain (new - current) as a match for it)
  python apex_stats.py c        (quick-start cheat sheet)
  python apex_stats.py          (interactive mode: "<kills> <wins> [legend] [level]", <n>, <n>l,
                                 <n>k, <n>w, account [kills] [wins], base <legend> <kills> <wins>,
                                 report, l, k, w, m, lv, undo, c, date YYYY-MM-DD | date today;
                                 an empty line quits)
  Sticky legend (interactive mode): a typed legend is remembered and reused by later matches and
  account entries that omit it; typing another legend replaces it ("-" clears it). <n>k / <n>w
  never use it.
  Every match adds its kills/wins to its legend's all-time totals (base + logged) and to the
  global account totals.
  Terminal numbers use thousands separators (15,000); kills/wins input may use them too.
  Global option: --dir <folder>  (default: ./apex_data next to the script)

Smart parsing of [legend] [level]: if the 3rd value is a number it is the level (no legend),
otherwise it is the legend and a trailing number is the level.
Every level value, in full entries and level-only input alike: "700" = absolute level (rejected if
lower than the last recorded level), "+3" = last recorded level + 3.

"level" is the account level reached (0 = not recorded). It can never go down: a new level
must be >= the last level recorded before its date and <= the next level recorded after it.
"+<n>" records (last level recorded before the entry's date) + n.

Rotation by calendar month: one file per month (apex_stats_YYYY-MM.txt).
Global account totals (set with "account <kills> <wins>") and the per-legend bases (set with
"base <legend> <kills> <wins>") live in their own file, account_stats.txt, so they survive every
rotation; report, k and w show the account totals on top. Once set, every saved match adds its
kills/wins to them and undo subtracts them again.

Terminal output is colorized with raw ANSI codes (kills red, wins green) when stdout is a
terminal and NO_COLOR is not set. Data files never contain color codes.

File format (O(1) parsing per line via a constant prefix in the first column):
  @FILE  month of the file    @HIST  all-time totals of previous months
  @PREV  per-month totals (last 11 calendar months, for semiannual/annual)
  @HL    all-time totals per legend (previous months)
  @PL    per-month, per-legend totals (last 11 months)
  @LV    highest level reached per day (previous months, last year + 1 baseline)
  L      one log entry (date, legend, kills, wins, level, id)
  #      headers/comments (ignored by the parser)
  Summaries after "# SUMMARY" are recomputed on every write and never parsed.
"""
from apex.cli import main

if __name__ == "__main__":
    main()
