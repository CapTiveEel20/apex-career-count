# Apex Career Count

A terminal counter for your **Apex Legends** kills, wins and account level over time, by legend. Type a match in a few keystrokes and get all-time totals, per-period tables and your best games. Everything stays in plain `.txt` files on your own computer.

- Log a match with as little as `7` or `7 1 wraith`
- Totals per legend and for the whole account, kept across months
- Top games of the month and an all-time list of monthly bests
- `undo` for every action, last in, first out
- Python standard library only, nothing to install

## Getting started

You need Python 3.7 or newer.

```bash
python apex_career_count.py
```

This opens the interactive menu. Type `help` for what each command does, and press Enter on an empty line to quit. Your data is saved in `apex_data/` next to the script.

To build a standalone `.exe` that keeps its data next to it:

```bash
pyinstaller --onefile --distpath . apex_career_count.py
```

### First session

```
> account 15000 900 700      ← your current kills, wins and level
> base wraith 3000 150       ← a legend's current kills and wins
> 7 1 wra                    ← a match: 7 kills, 1 win, Wraith
SAVED  Wraith  KILLS 7  WINS 1  LEVEL 700  (2026-11-09 21:42)
TOTALS -> [Wraith] K: 3,007 W: 151 | [ACCOUNT] K: 15,007 W: 901
```

## Logging

### Matches

| Input | What it saves |
|---|---|
| `7` | 7 kills, 0 wins, no legend. With a sticky legend: 7 kills and 1 win for it, the same as `7 <legend>` |
| `5 1` | 5 kills, 1 win, no legend (or the sticky legend) |
| `5 1 wraith` | 5 kills, 1 win, Wraith |
| `5 wraith` | 5 kills, **1 win (added automatically)**, Wraith |
| `5k` / `5k wraith` | 5 kills only |
| `1w` / `1w wraith` | 1 win only |
| `5k 1w 2l wraith` | 5 kills, 1 win and 2 levels, Wraith |
| `5k 2l` | 5 kills and 2 levels, no legend (or the sticky legend) |

With plain numbers, kills always come first and no level is allowed. To add levels with a match, use `<n>k [<n>w] [<n>l] [legend]`: leave out any you don't need, but keep that order and put the legend last. In this form wins are never added automatically. Adding levels needs a level already recorded (`accountl`), and one `undo` reverts the whole line.

Legend names can be shortened: `7 1 wra` saves Wraith if it is the only known legend starting with `wra`. If several match, type more letters. A name nobody knows asks `Unknown legend '<name>'. Create new? (y/n):`, and anything but `y` saves nothing.

### Account and legend totals

| Input | What it does |
|---|---|
| `account <kills> <wins> [level]` | The first time, saves your all-time totals. After that, logs the gain (new minus saved). |
| `account` | Shows the account totals and your current level |
| `base <legend> <kills> <wins>` | The first time, sets a legend's all-time totals. After that, logs the gain for that legend and adds it to the account totals. |
| `base` | Lists the legends with a base |
| `base <legend> 0 0` | Removes a legend's base |

Every match is added to the account totals and to its legend's totals automatically.

### Levels

| Input | What it does |
|---|---|
| `accountl 700` | Sets your account level |
| `3l` | Adds 3 levels (takes no legend on its own) |
| `5k 3l wraith` | Adds 3 levels together with a match |

> [!NOTE]
> `account`, `base` and `accountl` ask `Warning: New value is lower than current. Proceed? (y/n):` before lowering a value. Only `y` proceeds. A confirmed lowering logs nothing, and `undo` reverts it.

### Sticky legend

The sticky legend is **off** by default. `p <name>` locks a legend already set with `base`, and matches and `<n>k [<n>w] [<n>l]` entries without a legend then use it. While it is locked, a number alone counts as 1 win, exactly like typing the legend; use `7 0` to save a match with no win. A legend typed in an entry is used for that entry only. A typed `-` unlocks it, and `-` on a line of its own saves nothing.

```
> p bangalore
[Bangalore]> 3 0
[Bangalore]> 2k         ← saved as Bangalore
[Bangalore]> -
>
```

### Dates

`date YYYY-MM-DD` saves the next entries on that day, and `date today` goes back to today. Future days are refused. Once a newer month has a file, earlier months are closed to new entries.

### Undo

`undo` reverts the most recent action, whether a match, a level update, a base change or an account change, and restores the previous totals exactly. It works through the newest month's actions, then back into the month before. Each undo shows what the next one would revert:

```
Undone: 2026-11-06 21:42 | - | WINS 0 | KILLS 0 | LEVEL 58  (3 logs left in 2026-11)
PREVIOUS LOG: [MATCH] 2026-11-06 21:41 | Legend: Wraith | KILLS 4 | WINS 1
```

## Tables

| Command | Shows |
|---|---|
| `l` | Base legends' all-time totals, most kills first, with each one's last match, next to the top 3 legends by kills this month |
| `lw` / `la` / `lm` | Same, sorted by wins / name / most recent match |
| `ls <name>` | Same, only the base legends whose name contains `<name>` |
| `g` | This month's top 10 games by kills (win or loss shown, never ranked on), next to the all-time top 6 monthly bests |
| `k` / `w` | Kills / wins per legend for the month, semiannual, annual and all-time, with a `GRAND TOTAL` |
| `report` | Account totals, then kills and wins over the last week, month, 3 months, 6 months, year and all-time, next to the levels gained over the same periods |
| `log` | This month's last 20 matches, next to the last 20 levels and the change from the previous one |

Gains logged by `account` and `base` are not single matches, so they never appear in `log`, `g` or a legend's last match.

## Your data

- There is one file per month (`apex_stats_YYYY-MM.txt`). Account totals and legend bases are in `account_stats.txt`. Both are aligned text tables you can read in any editor.
- Every save is written to a temporary file, flushed to disk and then swapped in.
- A line that can't be read is skipped with a warning and kept in the file as `@BAD`, so you can fix it by hand. If the `@ACCOUNT` line itself is damaged, saving stops with an error until it is fixed.
- `.gitignore` keeps your data files and the `.exe` out of git.

## Tests

```bash
python -m unittest
```

Run this from the project folder. The tests use temporary folders and never touch `apex_data/`.
