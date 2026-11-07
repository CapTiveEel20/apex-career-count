# Apex Stats

A command-line tracker for your **Apex Legends** kills, wins and account level, by legend. Your data is kept in plain `.txt` files on your own computer. It uses only the Python standard library.

## Run

```bash
python apex_stats.py        # interactive mode (Enter on an empty line quits)
python apex_stats.py c      # cheat sheet
```

You need Python 3.7 or newer. Data is saved in `apex_data/` next to the script. To build an `.exe`, run `pyinstaller --onefile apex_stats.py`.

## Setup: account and base

| Input | What it does |
|---|---|
| `account <kills> <wins>` | The first time, saves your all-time account totals. After that, logs the gain (new - saved). |
| `account` | Shows the account totals and your current level. |
| `base <legend> <kills> <wins>` | The first time, sets a legend's all-time totals (nothing is logged). After that, logs the gain for that legend: it shows in `report` and is added to the account totals. |
| `base` | Lists the legends with a base. `base <legend> 0 0` removes one. |

- `account` takes kills and wins only. Totals lower than the saved ones are an error, and nothing changes.
- Every match is added to the account totals and to its legend's totals automatically.
- Base and account gains are not single matches: they never appear in `log`, the top 5 matches or a legend's last match.

## Matches

| Input | What it saves |
|---|---|
| `5 1 wraith` | 5 kills, 1 win, Wraith |
| `5 1` | 5 kills, 1 win, no legend |
| `5 wraith` | 5 kills, **1 win (added automatically)**, Wraith |

- Kills always come first.
- Matches take no level.
- The `SAVED` line shows your current account level.

## Levels and quick shortcuts

| Input | What it does |
|---|---|
| `700` | Sets your account level (it can never go down) |
| `3l` (or `+3`) | Adds 3 levels |
| `5k` | 5 kills only |
| `1w` | 1 win only |
| `5k wraith` | 5 kills only, for Wraith (also `1w wraith`) |

## Sticky legend (interactive mode)

The sticky legend is **OFF** by default.

- `p` turns it ON or OFF.
- While it is ON, the legend you type is pinned. Matches without a legend use it, and so do `<n>k` and `<n>w` (unless you type a legend after them, e.g. `5k wraith`).
- `-` unpins the legend and turns sticky OFF (on a line of its own it saves nothing).

```
> p
[sticky ON]> 3 0 bangalore
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
| `l` | Base legends' all-time totals (most kills first) with the date and time of their last match, next to the top 3 legends by kills this month |
| `lw` / `la` / `lm` | Same, sorted by wins / name / last match (most recent first) |
| `ls <name>` | Same, only the base legends whose name contains `<name>` (e.g. `ls wra`) |
| `lv` | Levels gained over 1 week, 1/3/6 months and 1 year |
| `k` / `w` | Kills / wins per legend for each period, with a `GRAND TOTAL` |
| `log` | Matches only: this month's matches (no `account`/`base` gains or level updates) |
| `logl` | Levels only: level history, with the change from the previous level |

In a terminal, kills are shown in red, wins in green and levels in orange.

## Command line

Every input also works as a one-off command. Matches need `add`:

```bash
python apex_stats.py add 5 1 wraith
python apex_stats.py add 6 wraith --date "2026-11-05 21:30"
python apex_stats.py 700
python apex_stats.py account 12007 451
python apex_stats.py report
python apex_stats.py --dir D:/backup lv
```

- `--date "YYYY-MM-DD[ HH:MM]"` sets an entry's date.
- `--l NAME` sets the legend of `add`.
- `--dir <path>` uses another data folder.

In interactive mode, use `date YYYY-MM-DD` or `date today` instead of `--date`.

## Data and privacy

- There is one file per month (`apex_stats_YYYY-MM.txt`). The account totals and legend bases are in `account_stats.txt`.
- Every write is atomic.
- The files are aligned text tables you can read in any editor.
- `.gitignore` keeps your data files and the `.exe` out of git.
