# Apex Stats

A lightweight command-line tracker for your **Apex Legends** sessions. Log wins, kills and your account level, optionally tagged by legend, and get monthly, semiannual, annual and all-time summaries, plus how many levels you gained over rolling time windows. Everything is stored in plain, human-readable `.txt` files on your own machine.

- Run it with `apex_stats.py`; the code lives in the small `apex/` package next to it
- Zero dependencies: Python standard library only
- Your data never leaves your computer

---

## Features

- **Fast logging.** Record a session with one command, or type entries one after another in interactive mode.
- **Smart input.** Type `<kills> <wins> [legend] [level]`. The script works out on its own whether the third value is a legend or a level.
- **Level tracking.** Record your account level with a session, or on its own:
  - type just the level (`700`), or
  - type `<n>l` (`3l`) to add levels to your last recorded level. `+3` still works too.

  `lv` shows how many levels you gained in the last week, 1 month, 3 months, 6 months and year.
- **Level validation.** Your level can't go down. An entry with a level lower than the last one recorded is rejected.
- **Undo.** `undo` removes the most recently added entry. Repeat it to keep stepping back, one entry at a time.
- **Custom dates.** On the command line, `--date` works for both full entries and level-only entries. In interactive mode, set a date once (`date 2026-11-05`) and every following entry uses it.
- **Per-legend tracking.** `l` shows the all-time kills and wins of every legend. `k` and `w` show kills or wins per legend over the month, semiannual, annual and all-time periods.
- **Legend bases.** `base <legend> <kills> <wins>` sets a legend's all-time totals, for example the numbers on its in-game stats card. Entries already logged for that legend are counted inside them, not added on top. After that, typing the legend's new totals logs the difference as a match, just like `account`.
- **Everything stays in sync.** Every match you log is added both to its legend's all-time totals and to your global account totals. `undo` takes it back out of both.
- **Calendar-based files.** One file per month (`apex_stats_YYYY-MM.txt`), started automatically when a new month begins.
- **Cheap on disk access.** Each new month's file carries forward the totals of earlier months, so the script never has to reopen old files. Every operation reads one file and writes at most one.
- **Safe writes.** Files are written to a temporary file first and then swapped in. A crash or power loss can't leave a half-written log.
- **Readable files.** The data files are aligned tables you can open in any text editor.
- **Consistent legend names.** `WRAITH`, `wraith` and `Wraith` are all saved as `Wraith`.
- **Global account totals.** `account <kills> <wins>` saves your all-time career totals, for example the numbers shown in game, in their own file. After that, every new match is added to them automatically and `undo` takes it back out. They are never lost when a new month starts. `report`, `k` and `w` show them at the top.
- **Update from the game.** Once your account totals are saved, `account <kills> <wins>` with the new all-time totals shown in game logs the difference as a match. You don't have to work out the numbers yourself.
- **Quick entries.** `5k` logs 5 kills only, `1w` logs 1 win only (no legend), `3l` adds 3 levels and `700` sets your level.
- **Sticky legend.** In interactive mode, the last legend you typed is reused by later matches and account updates that leave it out.
- **Readable numbers.** All numbers in the terminal use thousands separators, such as `15,000`. You can type kills and wins the same way.
- **Colored output.** In a terminal, everything about kills is shown in red and everything about wins in green. This uses plain ANSI escape codes, with no extra libraries.

---

## Requirements

- Python **3.7 or newer**
- No packages to install

---

## Installation

```bash
git clone <your-repo-url>
cd <repo-folder>
python apex_stats.py -h
```

The script creates its data folder, `apex_data/`, next to `apex_stats.py` the first time you log an entry.

---

## Quick start

```bash
# 5 kills, 1 win, playing Wraith, account now at level 57
python apex_stats.py add 5 1 wraith 57

# Record just your level (a single number), or add levels with <n>l
python apex_stats.py 58
python apex_stats.py 2l

# Quick entries: 3 kills only, 1 win only (no legend)
python apex_stats.py 3k
python apex_stats.py 1w

# See the levels you have gained
python apex_stats.py lv

# See this month's summaries
python apex_stats.py report

# Save your global all-time account totals (kills, then wins) and show them
python apex_stats.py account 12000 450
python apex_stats.py account

# Later: type the new all-time totals shown in game; the difference is logged as a match
python apex_stats.py account 12007 451 wraith

# Set a legend's all-time totals (e.g. from its in-game stats card), then see all legends
python apex_stats.py base wraith 3000 120
python apex_stats.py l

# Later: type the legend's new all-time totals; the difference is logged as a Wraith match
python apex_stats.py base wraith 3008 121

# Made a mistake? Remove the last entry
python apex_stats.py undo

# Or open interactive mode and type entries quickly
python apex_stats.py
```

---

## Entry format

Each entry follows the same pattern, on the command line and in interactive mode:

```
<kills> <wins> [legend] [level]
```

**Kills come first, then wins.** The two optional values are read like this:

| You type | Legend | Level |
|---|---|---|
| `693` | `-` (none) | 693. A single number on its own is a level update, with wins and kills set to 0. |
| `3l` or `+3` | `-` (none) | Last recorded level + 3. A relative level update, with wins and kills set to 0. |
| `5k` | `-` (none) | not recorded. 5 kills only, 0 wins. Never uses a legend. |
| `1w` | `-` (none) | not recorded. 1 win only, 0 kills. Never uses a legend. |
| `5 1` | `-` (none) | not recorded |
| `5 1 wraith` | `Wraith` | not recorded |
| `5 1 57` | `-` (none) | 57 (the third value is a number, so it's the level) |
| `5 1 wraith 57` | `Wraith` | 57 |
| `2 0 mad maggie 58` | `Mad maggie` | 58 (legends can contain spaces) |
| `5 1 +3` | `-` (none) | Last recorded level + 3 |
| `5 1 wraith +3` | `Wraith` | Last recorded level + 3 |

Rules:

- Kills, wins and level must be whole numbers, 0 or more. Kills and wins may use thousands separators (`15,000`). A level-only update (`<n>`, `<n>l` or `+<n>`), any `+<n>` increment and the `n` of `<n>k` / `<n>w` must be 1 or more.
- `<n>k`, `<n>w` and `<n>l` are single values: nothing can follow them.
- When the third value is a level, nothing can follow it.
- Legend names are saved with a capital first letter and the rest lowercase. A `|` typed in a legend name is saved as `/`.

### About levels

The level is your **account level at the time of the entry**, not the number of levels you gained. A level of 0, or no level at all, means "not recorded".

Every level value is read the same way, whether it is part of a full entry (`5 1 wraith 700`, `5 1 +3`) or typed on its own (`700`, `+3`), and whether or not a legend is given:

- **Absolute: `<n>` (no `+`).** Records level `n`, which becomes your new current level. It is rejected if it is lower than the last recorded level.
- **Relative: `<n>l` on its own, or `+<n>`.** Takes the last level recorded before the entry's date and adds `n` to it. The result is saved as an absolute level. If no level has been recorded yet, it is rejected, so enter an absolute level first.

Because an account level only goes up, the script checks each new level against the levels around its date. This applies to every way of recording a level, in full entries and level-only updates alike:

- It is **rejected if it is lower** than the last level recorded before its date.
- It is **rejected if it is higher** than a level recorded after its date. This can only happen with back-dated entries.

```
> 60
SAVED - LEVEL 60 (2026-11-06)
> 2l
SAVED - LEVEL 62 (2026-11-06)
> 5 1 wraith +3
SAVED  Wraith  WINS 1  KILLS 5  LEVEL 65  (2026-11-06 21:40)
> 2 0 +1
SAVED  -  WINS 0  KILLS 2  LEVEL 66  (2026-11-06 21:45)
> 59
Error: level 59 is lower than the last recorded level (66).
```

---

## Interactive mode (REPL)

Run the script with **no arguments** to open a quick-entry prompt:

```
$ python apex_stats.py
===============================================================================
                              APEX STATS TRACKER
===============================================================================
 [ SETUP ]   account <kills> <wins> (1st: saves totals; later: logs new - old)
 [ BASE ]    base <legend> <kills> <wins> (1st: sets total; later: logs gain)
 [ MATCH ]   <kills> <wins> [legend] [level] (e.g. 5 1 wraith 57 | 5 1 57)
 [ QUICK ]   <n>k | <n>w (kills only | wins only, no legend; e.g. 5k | 1w)
 [ LEVEL ]   <n> | <n>l (e.g. 700 sets level 700 | 3l adds 3 levels)
 [ REPORT ]  report | l | k | w | m | lv
 [ TOOLS ]   undo | date YYYY-MM-DD | date today | c (help)
 [ LEGEND ]  sticky: the last legend typed is reused by matches ("-" clears)
-------------------------------------------------------------------------------
 Press Enter on an empty line to quit.
> 5 1 wraith 57
SAVED  Wraith  WINS 1  KILLS 5  LEVEL 57  (2026-11-06 21:30)
> 1l
SAVED - LEVEL 58 (2026-11-06)
> undo
Undone: 2026-11-06 21:31 | - | WINS 0 | KILLS 0 | LEVEL 58  (1 log left in 2026-11)
> account 12000 450
SAVED - ACCOUNT  KILLS 12,000  |  WINS 450  (global, all-time; updated 2026-11-06 21:31)
> base bangalore 2500 90
SAVED - BASE  Bangalore  KILLS 2,500  |  WINS 90  (all-time totals of this legend)
> 3 0 bangalore
SAVED  Bangalore  WINS 0  KILLS 3  LEVEL 0  (2026-11-06 21:33)
[Bangalore]> 2 1
SAVED  Bangalore  WINS 1  KILLS 2  LEVEL 0  (2026-11-06 21:40)
[Bangalore]> 2k
SAVED  -  WINS 0  KILLS 2  LEVEL 0  (2026-11-06 21:52)
[Bangalore]> account 12,013 452
ACCOUNT  KILLS 12,007 -> 12,013 (+6)  |  WINS 451 -> 452 (+1)
SAVED  Bangalore  WINS 1  KILLS 6  LEVEL 0  (2026-11-06 22:05)
[Bangalore]> 4 0 -
SAVED  -  WINS 0  KILLS 4  LEVEL 0  (2026-11-06 22:10)
> date 2026-11-07
  Active date: 2026-11-07
[2026-11-07]> 4 0 lifeline 58
SAVED  Lifeline  WINS 0  KILLS 4  LEVEL 58  (2026-11-07 21:32)
[2026-11-07]> date today
  Active date: today (system)
>
```

The menu at the top is the **quick guide**, shown as soon as the prompt opens. `account` comes first, so you can set your global totals before anything else. The last line is an empty input (just Enter), which closes the prompt.

**Sticky legend.** When you type a legend in an entry, the prompt remembers it and shows it, e.g. `[Bangalore]>`. Later matches and `account` updates that leave the legend out use the remembered one instead of `-`. Typing another legend replaces it, and typing `-` as the legend (`4 0 -`) clears it. The quick entries `<n>k` and `<n>w` are independent: they never use the sticky legend and never change it. Level-only updates (`700`, `3l`) never use it either. The memory lasts until you close the prompt. With a custom date active, the prompt shows both, e.g. `[2026-11-07 | Bangalore]>`.

If you type something the prompt doesn't recognize or can't parse, it shows the quick guide again. Examples are an unknown command, `help`, `lv 5`, `5 x`, `3x`, `5k wraith`, `account 5`, `base wraith 5` or a malformed `date`. Input that is well-formed but breaks a rule gets a specific error message instead, such as a level lower than the last one recorded.

| Input | What it does |
|---|---|
| `<kills> <wins> [legend] [level]` | Saves an entry (see [Entry format](#entry-format)). |
| `<n>` (a single number) | Records level `n` on its own, with wins and kills set to 0 and the legend set to `-`. `n` must be 1 or more. |
| `<n>l` (or `+<n>`) | Adds `n` to the last recorded level and saves the result as a level-only entry, e.g. `3l`. |
| `<n>k` | Logs `n` kills and 0 wins, with no legend, e.g. `5k`. `n` must be 1 or more. |
| `<n>w` | Logs `n` wins and 0 kills, with no legend, e.g. `1w`. |
| `lv` | Shows levels gained over rolling time windows. It never records a level, so `lv 5` is rejected and shows the quick guide. |
| `undo` | Removes the most recently added entry. Repeat it to go further back. |
| `account` | Shows your saved global account totals (see [`account`](#account-global-account-totals)). |
| `account <kills> <wins> [legend] [level]` | The first time, saves your global all-time account totals, kills first. After that, logs the difference between these new totals and the saved ones as a match (see [`account`](#account-global-account-totals)). |
| `base <legend> <kills> <wins>` | The first time for a legend, sets its all-time totals. After that, logs the difference between these new totals and its current ones as a match for that legend (see [`base`](#base-legend-totals)). `base` on its own lists the legends with a base. |
| `date YYYY-MM-DD` | Uses this date for every following entry, both full entries and level-only updates. The time is taken from the clock when each entry is saved. While a custom date is active, the prompt shows it, e.g. `[2026-11-07]>`. |
| `date today` | Goes back to the system date. |
| `m` | Shows total kills and wins for the current month. |
| `report` | Shows your global account totals, then the match summaries, then the level report (same as `lv`). |
| `l` | Shows one all-time table: total kills and wins per legend, base plus logged entries. Entries without a legend are excluded. |
| `k` | Shows your global account kills, then kills only, per legend: month, semiannual, annual and all-time total, plus a `GRAND TOTAL` row for all legends combined. |
| `w` | Shows your global account wins, then wins only, per legend: month, semiannual, annual and all-time total, plus a `GRAND TOTAL` row for all legends combined. |
| `c` | Shows the quick-start cheat sheet: the input formats, a one-line list of every command and the main rules. This is the only help command. |
| *(empty line)* | Press Enter without typing anything to exit. This is the only exit command; `q` is not one. If the input stream closes, for example with `Ctrl+Z`/`Ctrl+D` or `Ctrl+C`, the prompt also stops cleanly. |

Each entry is saved immediately, the same way as with `add`, and confirmed with a `SAVED` line. Level-only updates show just the level and the day, e.g. `SAVED - LEVEL 693 (2026-11-06)`. An `account` update that logs a match first prints an `ACCOUNT` line with the old and new totals. After bad input the prompt stays open. Interactive mode always uses the default `apex_data/` folder.

---

## CLI commands

```
python apex_stats.py add <kills> <wins> [legend] [level] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
python apex_stats.py <n> | <n>l | +<n> [--date "YYYY-MM-DD[ HH:MM]"]
python apex_stats.py <n>k | <n>w [--date "YYYY-MM-DD[ HH:MM]"]
python apex_stats.py lv
python apex_stats.py undo
python apex_stats.py report
python apex_stats.py l
python apex_stats.py k
python apex_stats.py w
python apex_stats.py m
python apex_stats.py account [<kills> <wins> [legend] [level]] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
python apex_stats.py base [<legend> <kills> <wins>] [--date "YYYY-MM-DD[ HH:MM]"]
python apex_stats.py c
python apex_stats.py --dir <path> <command> ...
python apex_stats.py
```

There is no `help` command. Use `c` instead, both on the command line and in interactive mode. It shows the quick-start cheat sheet with every input format and command. If you mistype a command on the command line, the script prints the correct usage.

### `add`: log a session

```bash
python apex_stats.py add <kills> <wins> [legend] [level] [--l NAME] [--date "YYYY-MM-DD[ HH:MM]"]
```

| Argument | Required | Description |
|---|---|---|
| `<kills>` | yes | Kills in the session |
| `<wins>` | yes | Wins in the session |
| `[legend] [level]` | no | Legend and/or account level, read as described in [Entry format](#entry-format) |
| `--l NAME` | no | Sets the legend explicitly. It overrides a legend typed as a positional value. |
| `--date "YYYY-MM-DD[ HH:MM]"` | no | When the session happened. Defaults to now. If you give only the day, the current time is used. |

Examples:

```bash
python apex_stats.py add 7 1 bloodhound 57
python apex_stats.py add 3 0 58                           # level 58, no legend
python apex_stats.py add 4 1 wraith +2                    # last recorded level + 2
python apex_stats.py add 2 0 +1                           # last recorded level + 1, no legend
python apex_stats.py add 3 0 --l "mad maggie" --date "2026-11-05 21:30"
python apex_stats.py add 9 2 horizon --date 2026-11-04
```

`add` always needs at least kills and wins. To record a level on its own, see [Level updates](#quick-entries-n-nl-nk-and-nw).

After saving, the command prints a `SAVED` line and the updated summaries:

```
SAVED  Bloodhound  WINS 1  KILLS 7  LEVEL 57  (2026-11-06 21:30)
```

> **Note:** you can't add an entry dated in a month earlier than the newest file. That month is closed, and its totals have already been carried into the newer file.

### Quick entries: `<n>`, `<n>l`, `<n>k` and `<n>w`

Pass a single value with no command for a quick entry. The legend is always `-`.

| Input | What it records |
|---|---|
| `<n>` | Level `n` (absolute), with wins and kills set to 0 |
| `<n>l` or `+<n>` | The last level recorded before the entry's date, plus `n` (relative), with wins and kills set to 0 |
| `<n>k` | `n` kills and 0 wins, no level |
| `<n>w` | `n` wins and 0 kills, no level |

`<n>k` and `<n>w` count toward your account totals like any match. Because they have no legend, they don't show up in `l`, `k` or `w`.

`--date` sets when the level was reached, just like with `add`, and `--dir` works as usual:

```bash
python apex_stats.py 58
python apex_stats.py 2l
python apex_stats.py 5k
python apex_stats.py 1w --date 2026-11-02
python apex_stats.py 59 --date 2026-11-02
python apex_stats.py +1 --date "2026-11-03 18:45"
```

```
SAVED - LEVEL 60 (2026-11-03)
```

### `lv`: levels gained

`lv` only shows the level report. It never records a level.

```bash
python apex_stats.py lv
```

```
# LEVELS GAINED  (today: 2026-11-06, current level: 694)
PERIOD        | FROM       |  GAINED
------------------------------------
1 WEEK        | 2026-10-30 |       4
1 MONTH       | 2026-10-06 |      12
3 MONTHS      | 2026-08-06 |      31
6 MONTHS      | 2026-05-06 |      58
1 YEAR        | 2025-11-06 |     104
====================================
```

How `GAINED` is calculated:

- The windows are counted back from **today's system date**, and each one covers the days after `FROM` up to and including today.
- `GAINED` is your current level minus the last level recorded on or before `FROM`.
- If no level was recorded before the window starts, the first level recorded inside the window is used instead.
- Month windows go back by calendar months, so "1 month" on 6 November starts from 6 October.


### `undo`: remove the last entry

```bash
python apex_stats.py undo
```

```
Undone: 2026-11-06 21:31 | - | WINS 0 | KILLS 0 | LEVEL 58  (1 log left in 2026-11)
```

`undo` removes the entry that was **added most recently**, even if you gave it an earlier date. Run it again to remove the one before that, and so on.

When `undo` removes the last entry of a month, that month's file is deleted and the previous month becomes the current file again. Further `undo` calls continue in that month. Older files are never changed when a new month starts, so they are still exactly as they were.

### `report`: match and level statistics

```bash
python apex_stats.py report
```

This prints your global account totals first (see [`account`](#account-global-account-totals)), then the match summaries, then the level report directly below them. The level report is exactly the output of [`lv`](#lv-levels-gained).

```
ACCOUNT  KILLS 12000  |  WINS 450  (global, all-time; updated 2026-11-06 21:31)

# SUMMARY  (updated: 2026-11-06 22:59)
REFERENCE     |    KILLS |     WINS
-----------------------------------
MONTH 2026-11 |       22 |        2
SEMIANNUAL    |       41 |        6
ANNUAL        |       67 |        9
ALL-TIME      |       85 |       11
===================================

# LEVELS GAINED  (today: 2026-11-06, current level: 694)
PERIOD        | FROM       |  GAINED
------------------------------------
1 WEEK        | 2026-10-30 |       4
...
```

| Row | Period covered |
|---|---|
| `MONTH YYYY-MM` | The current month |
| `SEMIANNUAL` | The current month and the 5 months before it |
| `ANNUAL` | The current month and the 11 months before it |
| `ALL-TIME` | Everything ever recorded |

The report tables show only kills, wins and levels, never a count of entries. The `ACCOUNT` line shows the totals you saved with `account`. It is separate from the tables below it, which count only the matches logged with this tool. If you haven't saved account totals yet, it reads `ACCOUNT  not set yet (use: account <kills> <wins>)`.

### `l`: all-time totals by legend

```bash
python apex_stats.py l
```

One all-time table, with no time periods: the total kills and wins of every legend. Each total is the legend's [base](#base-legend-totals) plus every entry you have logged for it, so after `base wraith 3000 120` Wraith shows exactly 3,000 kills and 120 wins, then grows with every match. Only real legend names are listed. Entries without a legend, such as level-only updates, `<n>k` / `<n>w` quick entries or matches saved without a legend, are left out of this table. They still count in `report` and in the account totals.

```
# ALL-TIME BY LEGEND  (base + logged entries; current month: 2026-11)
# LEGEND     |    KILLS |     WINS
----------------------------------
Bangalore    |    2,511 |       92
Wraith       |       15 |        5
----------------------------------
GRAND TOTAL  |    2,526 |       97
==================================
```

### `k` and `w`: kills or wins per legend

```bash
python apex_stats.py k
python apex_stats.py w
```

These show a single statistic per legend in one compact table: `k` shows kills and `w` shows wins. Each row breaks the value down by period. `ALL-TIME` is the absolute historical total for that legend.

The last row, `GRAND TOTAL`, adds up every legend for each period. Its `ALL-TIME` value is your all-time total of kills (`k`) or wins (`w`) across all legends.

At the top, `k` shows your global account kills and `w` shows your global account wins, as saved with [`account`](#account-global-account-totals).

```
ACCOUNT  KILLS 12000  (global, all-time; updated 2026-11-06 21:31)

# KILLS BY LEGEND  (current month: 2026-11)
# LEGEND     |    MONTH | SEMIANNUAL |   ANNUAL | ALL-TIME
----------------------------------------------------------
Lifeline     |        0 |          4 |        6 |        8
Wraith       |        4 |         10 |       13 |       16
----------------------------------------------------------
GRAND TOTAL  |        4 |         14 |       19 |       24
==========================================================
```

The periods are the same as in [`report`](#report-match-and-level-statistics). The `ALL-TIME` column also includes the legend's [base](#base-legend-totals), so it matches `l`. Like `l`, these tables list only real legends: level-only updates and other entries without a legend are excluded, including from the `GRAND TOTAL`.

### `c`: quick-start cheat sheet

```bash
python apex_stats.py c
```

The only help command. It uses the same layout as the quick guide: the same banner and `[ SETUP ]`, `[ BASE ]`, `[ MATCH ]`, `[ QUICK ]`, `[ LEVEL ]`, `[ REPORT ]` and `[ TOOLS ]` sections. Each command gets a one-line description, and a `[ RULES ]` section follows. In a terminal, kill-related text, including `k`, is red, and win-related text, including `w`, is green.

```

===============================================================================
                              APEX STATS TRACKER
===============================================================================
 [ SETUP ]   account <kills> <wins>                   1st time: save your all-time totals (e.g. account 15000 800)
             account <kills> <wins> [legend] [level]  later: log the gain (new - saved) as a match
             account                                  show the saved global account totals
 [ BASE ]    base <legend> <kills> <wins>             1st time: set a legend's all-time totals (e.g. base wraith 3000 120)
             base <legend> <kills> <wins>             later: log the gain (new - current) as a match for it
             base                                     list the legends with a base and their all-time totals
 [ MATCH ]   <kills> <wins> [legend] [level]          save a match (e.g. 5 1 wraith 57 | 5 1 57)
             <kills> <wins> [legend] +<n>             match + n levels (e.g. 5 1 wraith +3 | 5 1 +3)
 [ QUICK ]   <n>k                                     n kills only: 0 wins, no legend (e.g. 5k)
             <n>w                                     n wins only: 0 kills, no legend (e.g. 1w)
 [ LEVEL ]   <n>                                      set your absolute level (e.g. 700)
             <n>l                                     add n to the current level (e.g. 3l; +3 works too)
 [ REPORT ]  report                                   account totals + match summaries + level report
             l                                        all-time kills and wins per legend (base + logged)
             k                                        account kills + kills per legend (+ grand total)
             w                                        account wins + wins per legend (+ grand total)
             m                                        kills and wins this month
             lv                                       levels gained (1 week ... 1 year)
 [ TOOLS ]   undo                                     remove the last entry (repeatable)
             date YYYY-MM-DD                          use this date for the next entries
             date today                               back to the system date
             c                                        this cheat sheet (help)
-------------------------------------------------------------------------------
 [ RULES ]   - Kills first, then wins; a numeric 3rd value is the level, text is the legend.
             - Legends are saved capitalized (wraith -> Wraith).
             - Every match adds its kills and wins to its legend's all-time totals
               (base + logged: l, k, w) and to the global account totals.
             - account: the 1st time saves your totals; later it logs (new - saved) as a
               match. Lower values only correct the totals. undo takes a match back out.
             - base: the 1st time sets the legend's all-time totals (logged entries
               included, nothing logged); later it logs (new - current) for that legend.
             - Level <n> = absolute (never lower than the last one); <n>l adds n to it.
             - <n>k and <n>w never use a legend.
             - Entries cannot be dated in a month older than the newest data file.
             - Numbers are shown with thousands separators (15,000); kills/wins may be typed so.
             - Sticky legend: a legend you type is reused by later matches and account
               entries that omit it, until you type another one ("-" clears it).
-------------------------------------------------------------------------------
 Press Enter on an empty line to quit.
```

That is the interactive version. On the command line, the match lines start with `add`, the quick and level lines start with `python apex_stats.py`, and the `date` lines are replaced by the `--date` option. The sticky-legend rule exists only in interactive mode, so the command-line version leaves it out.

### `account`: global account totals

```bash
python apex_stats.py account 12000 450              # 1st time: save your totals, kills first
python apex_stats.py account                        # show them
python apex_stats.py account 12007 451 wraith +1    # later: log the gain as a match
```

```
SAVED - ACCOUNT  KILLS 12,000  |  WINS 450  (global, all-time; updated 2026-11-06 21:31)
ACCOUNT  KILLS 12,000  |  WINS 450  (global, all-time; updated 2026-11-06 21:31)
ACCOUNT  KILLS 12,000 -> 12,007 (+7)  |  WINS 450 -> 451 (+1)
SAVED  Wraith  WINS 1  KILLS 7  LEVEL 59  (2026-11-06 22:40)
```

Use this for your career totals, for example the all-time kills and wins shown in game. They are saved in `apex_data/account_stats.txt`, a separate file that never rotates, so they are kept across months.

- **First time.** `account <kills> <wins>` just saves the totals. Nothing is logged, and a legend or level is rejected.
- **Afterwards.** Type the new all-time totals shown in game. The script subtracts the saved totals and logs the difference (new - saved) as a normal match entry, with an optional legend and level read as in [Entry format](#entry-format). The account totals then become the new values.
  - In interactive mode, an update without a legend uses the [sticky legend](#interactive-mode-repl). On the command line, use `--l NAME` or type the legend; `--date` works as with `add`.
  - If nothing changed and no level is given, nothing is logged (`already up to date`).
  - If a new value is lower than the saved one, it is treated as a correction: the totals are replaced and nothing is logged.
- Both values must be whole numbers, 0 or more, with or without thousands separators (`12000` or `12,000`).
- `account` with a single value, or with text, is rejected. In interactive mode it shows the quick guide.
- Once set, the totals stay up to date:
  - Every match you save, with `add`, an `account` update, `<n>k`, `<n>w` or in interactive mode, adds its kills and wins to them.
  - `undo` subtracts the kills and wins of the entry it removes, so the totals always match your log. An undone `account` update puts the totals back to their old values. Entries saved before you first set the totals were never added, so undoing them leaves the totals alone.
  - Level-only updates don't change them.
- Until you set them for the first time, saved matches leave them unset.
- They never go below 0.

`report` shows both totals at the top, `k` shows the account kills and `w` shows the account wins.

### `base`: legend totals

```bash
python apex_stats.py base wraith 3000 120        # 1st time: Wraith's all-time totals (kills, then wins)
python apex_stats.py base wraith 3008 121        # later: logs a Wraith match with +8 kills, +1 win
python apex_stats.py base "mad maggie" 50 2      # legends can contain spaces
python apex_stats.py base                        # list the legends with a base
python apex_stats.py base wraith 0 0             # remove Wraith's base
```

```
SAVED - BASE  Wraith  KILLS 3,000  |  WINS 120  (all-time totals of this legend)
BASE  Wraith  KILLS 3,000 -> 3,008 (+8)  |  WINS 120 -> 121 (+1)
SAVED  Wraith  WINS 1  KILLS 8  LEVEL 0  (2026-11-07 22:40)
```

Type a legend's **all-time** kills and wins, for example from its in-game stats card. `base` works like [`account`](#account-global-account-totals), but for one legend:

- **First time for a legend.** The values become that legend's all-time totals. Entries you have already logged for it are counted inside them, not added on top: if you logged 46 Rampart kills and then type `base rampart 254 7`, Rampart shows 254 kills, not 300. Nothing is logged, so your account totals don't change.
- **Afterwards.** Type the legend's new all-time totals. The difference (new - current) is logged as a normal match for that legend. Like every match, it is added to the legend's totals and to your global account totals, and `undo` takes it back out of both. `--date` (command line) or the `date` command (interactive mode) sets its date.
  - If nothing changed, nothing is logged (`already up to date`).
  - If a new value is lower than the current one, it is treated as a correction: the legend's totals are set to the new values and nothing is logged.
- The totals can't be lower than what is already logged for that legend.
- `0 0` removes the base. The legend's totals then count only its logged entries.
- `base` on its own lists every legend with a base and its current all-time totals.
- A legend's all-time totals in `l`, and the `ALL-TIME` column of `k` and `w`, include the base. Every new match for that legend is added on top automatically.
- Legend names are capitalized like in entries (`wraith` -> `Wraith`), so a base always matches that legend's entries.
- Bases are stored permanently in `apex_data/account_stats.txt`, next to the account totals, and never rotate. Each `@BASE` line holds only the part of the legend's totals that isn't covered by logged entries.

### Number format

All numbers shown in the terminal use thousands separators: tables, `SAVED`, `ACCOUNT` and `Undone` lines, `m`, `account`, `base`, levels and error messages (`15,000`, `LEVEL 1,205`). Kills and wins can be typed with separators too (`account 15,005 801`). The data files keep plain digits.

### Colors

When the output goes to a terminal, kills are shown in **red** and wins in **green**. This covers table headers and values, `SAVED`, `ACCOUNT` and `Undone` lines, `m`, `account`, `base`, the quick guide and the cheat sheet, including the `<n>k` (red) and `<n>w` (green) shortcuts. Plain ANSI escape codes are used, with no external libraries. On Windows, the script turns on the console's ANSI support itself.

Colors are switched off automatically when the output is redirected to a file or a pipe, and when the `NO_COLOR` environment variable is set. Data files never contain color codes.

### `m`: current month totals

```bash
python apex_stats.py m
```

```
MONTH 2026-11  |  KILLS 22  |  WINS 2
```

### `--dir`: custom data folder

`--dir` is a global option, so it goes **before** the command:

```bash
python apex_stats.py --dir D:/apex-backup add 5 1 octane 57
python apex_stats.py --dir D:/apex-backup lv
```

This is handy for testing or for keeping separate profiles.

---

## How data is stored

```
apex_data/
├── apex_stats_2026-09.txt
├── apex_stats_2026-10.txt
├── apex_stats_2026-11.txt   ← current file (newest month)
└── account_stats.txt        ← global account totals (`account`) and legend bases (`base`), never rotated
```

Each monthly file has three sections:

1. **Header.** The totals carried forward from earlier months:
   - the all-time totals of every earlier month,
   - per-month and per-legend totals for the last 11 months,
   - the highest level reached on each day over the last year.

   These carried-forward totals are what let the summaries, `lv` and the level checks work without opening older files.
2. **Log.** One row per entry: date, legend, kills, wins, level, an entry `ID` and an `ACC` flag. Rows are sorted by date. The `ID` records the order entries were added in, which is what `undo` follows. `ACC` is `1` when the entry's kills and wins were added to your global account totals. `undo` only subtracts from the account totals for those entries, so entries logged before you set the totals never throw them off.
3. **Summary.** The `report` table, recalculated every time the file is saved.

Example excerpt:

```
@FILE   | 2026-11
# TAG   | REFERENCE     |   LOGS |    KILLS |     WINS
-------------------------------------------------------------------------
@HIST   | < 2026-11     |     21 |       63 |       21
@PREV   | 2026-10       |      3 |        9 |        3
...
@LV     | 2026-10-28    |     690
...
# LOG   | DATE             | LEGEND       | KILLS |  WINS |  LEVEL |   ID | ACC
-------------------------------------------------------------------------
L       | 2026-11-06 22:30 | Wraith       |     5 |     1 |    694 |    1 |   1
```

The header lines still store an internal `LOGS` count of entries per period, to stay compatible with existing data files. It is never shown in the report tables.

The tag at the start of each line (`@FILE`, `@HIST`, `@PREV`, `@HL`, `@PL`, `@LV`, `L`) tells the script what the line holds, so a file can be read in one quick pass. If you edit a file by hand, keep the tags, the `|` separators and the column order. Inside the file, the kills column comes before the wins column, the same order you type them in.

Files from earlier versions of the script still load:

- Entries with no level column count as "level not recorded".
- Entries with no `ID` column are numbered in the order they appear in the file.
- Entries with no `ACC` column count as not added to the account totals.
- The file is rewritten in the current format the next time it is saved.

---

## Project structure

```
apex_stats.py          ← entry point: python apex_stats.py ... (or python -m apex ...)
apex/
├── config.py          ← constants: file names, tags, date formats, column widths
├── cli.py             ← command-line commands and options
├── core/              ← pure logic: input parsing, totals per period and legend, level rules
├── display/           ← colors, table formatting, summary table, short messages
├── storage/           ← monthly data files and account_stats.txt (always written atomically)
├── services/          ← saving entries, undo, account and base updates
└── ui/                ← reports, quick guide and cheat sheet, interactive mode
```

Each layer only uses the ones above it in this order: `config`, `core`, `display`, `storage`, `services`, `ui`, `cli`.

To build a standalone executable with PyInstaller, run `pyinstaller --onefile apex_stats.py`. The executable keeps its `apex_data/` folder next to itself.

---

## Privacy

Your logs are personal data. The included `.gitignore` keeps the `apex_data/` folder, all `apex_stats_*.txt` files and `account_stats.txt` out of git, so you can fork or contribute without publishing your match history.
