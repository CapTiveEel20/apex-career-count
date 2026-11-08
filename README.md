# Apex Stats

A terminal tracker for your **Apex Legends** kills, wins and account level, by legend. Your data is kept in plain `.txt` files on your own computer. It uses only the Python standard library.

## Run

```bash
python apex_stats.py
```

It opens the interactive menu. Type `help` to see what each command does, and press Enter on an empty line to quit.

You need Python 3.7 or newer. Data is saved in `apex_data/` next to the script. To build an `.exe`, run `pyinstaller --onefile apex_stats.py`.

## Setup: account and base

| Input | What it does |
|---|---|
| `account <kills> <wins>` | The first time, saves your all-time account totals. After that, logs the gain (new - saved). |
| `account <kills> <wins> <level>` | Same, and also sets your account level. |
| `account` | Shows the account totals and your current level. |
| `base <legend> <kills> <wins>` | The first time, sets a legend's all-time totals (nothing is logged). After that, logs the gain for that legend: it shows in `report` and is added to the account totals. |
| `base` | Lists the legends with a base. `base <legend> 0 0` removes one. |

- `account`, `base` and `accountl` ask `Warning: New value is lower than current. Proceed? (y/n):` before lowering a value. Only `y` proceeds. A confirmed lowering logs nothing, and `undo` reverts it.
- Every match is added to the account totals and to its legend's totals automatically.
- Base and account gains are not single matches: they never appear in `log`, the top 5 matches or a legend's last match.

## Matches

| Input | What it saves |
|---|---|
| `7` | 7 kills, 0 wins, no legend (or the sticky legend) |
| `5 1 wraith` | 5 kills, 1 win, Wraith |
| `5 1` | 5 kills, 1 win, no legend |
| `5 wraith` | 5 kills, **1 win (added automatically)**, Wraith |

- Kills always come first.
- Matches take no level.
- The `SAVED` line shows your current account level.

## Levels and quick shortcuts

| Input | What it does |
|---|---|
| `accountl 700` | Sets your account level (asks y/n if it is lower than the current one) |
| `3l` | Adds 3 levels |
| `5k` | 5 kills only |
| `1w` | 1 win only |
| `5k wraith` | 5 kills only, for Wraith (also `1w wraith`) |

## Sticky legend

The sticky legend is **OFF** by default.

- `p <name>` locks a legend already set with `base`. A missing or unknown name is an error and changes nothing.
- While it is locked, matches without a legend use it, and so do `<n>k` and `<n>w`. A legend typed in an entry (e.g. `5k wraith`) is used for that entry only.
- `-` clears the legend and turns sticky OFF (on a line of its own it saves nothing).

```
> p bangalore
[Bangalore]> 3 0
[Bangalore]> 2 1        ← saved as Bangalore
[Bangalore]> 2k         ← saved as Bangalore
[Bangalore]> -
>
```

## Undo

`undo` reverts the most recent action, last in, first out. That can be a match, a level update, a base change, or an account save or gain, and the previous totals are restored exactly. Each undo then shows the previous log (what the next undo would revert), labeled `[MATCH]`, `[ACCOUNT UPDATE]`, `[BASE UPDATE]` or `[LEVEL UPDATE]`:

```
Undone: 2026-11-06 21:42 | - | WINS 0 | KILLS 0 | LEVEL 58  (3 logs left in 2026-11)
PREVIOUS LOG: [MATCH] 2026-11-06 21:41 | Legend: Wraith | KILLS 4 | WINS 1
```

## Reports and history

| Command | Shows |
|---|---|
| `report` | Account totals, match summaries (month, semiannual, annual, all-time) and levels gained |
| `m` | Kills and wins this month + top 5 all-time highest-kill matches (kept across months) |
| `g` | Side by side: this month's top 10 games by kills (W/L shown, never ranked on) and the all-time top 6 monthly bests |
| `l` | Base legends' all-time totals (most kills first) with the date and time of their last match, next to the top 3 legends by kills this month |
| `lw` / `la` / `lm` | Same, sorted by wins / name / last match (most recent first) |
| `ls <name>` | Same, only the base legends whose name contains `<name>` (e.g. `ls wra`) |
| `k` / `w` | Kills / wins per legend for each period, with a `GRAND TOTAL` |
| `log` | Side by side: this month's last 20 matches (no `account`/`base` gains) and the last 20 levels, with the change from the previous level |

In a terminal, kills are shown in red, wins in green and levels in orange.

## Dates

Use `date YYYY-MM-DD` to save the next entries on that date, and `date today` to go back to today.

## Data and privacy

- There is one file per month (`apex_stats_YYYY-MM.txt`). The account totals and legend bases are in `account_stats.txt`.
- Every write is atomic.
- The files are aligned text tables you can read in any editor.
- `.gitignore` keeps your data files and the `.exe` out of git.
