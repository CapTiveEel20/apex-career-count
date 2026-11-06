# Apex Stats

A lightweight command-line tracker for your **Apex Legends** sessions. Log your kills and wins, optionally tagged by legend, and get monthly, six-month, yearly and all-time summaries. Everything is stored in plain, human-readable `.txt` files on your own machine.

- Single file: `apex_stats.py`
- Zero dependencies: Python standard library only
- Your data never leaves your computer

> The program's output and data files use Italian labels (e.g. `KILL`, `VITTORIE` = wins, `LEGGENDA` = legend, `SEMESTRALE` = six-month, `ANNUALE` = yearly, `STORICO` = all-time).

---

## Features

- **Fast logging.** Record a session with one command, or type entries one after another in interactive mode.
- **Per-legend tracking.** Tag each entry with a legend and see every summary broken down by legend.
- **Calendar-based files.** One file per month (`apex_stats_YYYY-MM.txt`), started automatically when a new month begins.
- **Time-based summaries.** Each summary shows the current month, the last 6 months, the last 12 months and all-time totals, plus kills per entry and wins per entry.
- **Cheap on disk access.** Each new month's file carries forward the totals of earlier months, so the script never has to reopen old files. Every operation reads one file and writes at most one.
- **Safe writes.** Files are written to a temporary file first and then swapped in. A crash or power loss can't leave a half-written log.
- **Readable files.** The data files are aligned tables you can open in any text editor.
- **Consistent legend names.** `WRAITH`, `wraith` and `Wraith` are all saved as `Wraith`.

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
# Log a session: 5 kills, 1 win, playing Wraith
python apex_stats.py add 5 1 --l wraith

# See this month's summaries
python apex_stats.py report

# Or open interactive mode and type entries quickly
python apex_stats.py
```

---

## Interactive mode (REPL)

Run the script with **no arguments** to open a quick-entry prompt:

```
$ python apex_stats.py
Modalita' rapida: "<kills> <wins> <legend>"  (es. 5 1 wraith)
Comandi: m | report | l   -   q o invio vuoto = esci
> 5 1 wraith
  OK  Wraith  KILL 5  VITTORIE 1  (2026-11: 1 log)
> 3 0 lifeline
  OK  Lifeline  KILL 3  VITTORIE 0  (2026-11: 2 log)
> 2 1
  OK  -  KILL 2  VITTORIE 1  (2026-11: 3 log)
> m
MESE 2026-11  |  KILL 10  |  VITTORIE 2
> q
```

| Input | What it does |
|---|---|
| `<kills> <wins> [legend]` | Saves an entry. Everything after the second number is the legend name, which can be left out. |
| `m` | Shows total kills and wins for the current month. |
| `report` | Shows the time-based summaries. |
| `l` | Shows the summaries broken down by legend. |
| `q` or an empty line | Exits. `Ctrl+C` and `Ctrl+D` also exit cleanly. |

Each entry is saved immediately, the same way as with `add`. Bad input prints an error and the prompt stays open. Entries are timestamped with the current date and time, and interactive mode always uses the default `apex_data/` folder.

---

## CLI commands

```
python apex_stats.py add <kills> <wins> [--l NAME] [--date "YYYY-MM-DD HH:MM"]
python apex_stats.py report
python apex_stats.py l
python apex_stats.py m
python apex_stats.py --dir <path> <command> ...
python apex_stats.py
```

Run `python apex_stats.py -h` or `python apex_stats.py <command> -h` for built-in help. If you mistype a command, the script prints the correct usage.

### `add`: log a session

```bash
python apex_stats.py add <kills> <wins> [--l NAME] [--date "YYYY-MM-DD HH:MM"]
```

| Argument | Required | Description |
|---|---|---|
| `<kills>` | yes | Kills in the session (whole number, 0 or more) |
| `<wins>` | yes | Wins in the session (whole number, 0 or more) |
| `--l NAME` | no | Legend played. Saved with a capital first letter and the rest lowercase. Defaults to `-`. |
| `--date "YYYY-MM-DD HH:MM"` | no | When the session happened. Defaults to now. |

Examples:

```bash
python apex_stats.py add 7 2 --l bloodhound
python apex_stats.py add 3 0 --l "mad maggie" --date "2026-11-05 21:30"
python apex_stats.py add 4 1
```

After saving, the command prints where the entry went and the updated summaries.

> **Note:** you can't add an entry dated in a month earlier than the newest file. That month is closed, and its totals have already been carried into the newer file.

### `report`: time-based summaries

```bash
python apex_stats.py report
```

```
# RESOCONTI  (aggiornati: 2026-11-06 22:59)
RIFERIMENTO  |    LOG |     KILL | VITTORIE | KILL/LOG | WIN/LOG
----------------------------------------------------------------
MESE 2026-11 |      2 |        8 |        1 |     4.00 |    0.50
SEMESTRALE   |      9 |       27 |        9 |     3.00 |    1.00
ANNUALE      |     18 |       54 |       18 |     3.00 |    1.00
STORICO      |     24 |       72 |       24 |     3.00 |    1.00
================================================================
```

| Row | Period covered |
|---|---|
| `MESE YYYY-MM` | The current month |
| `SEMESTRALE` | The current month and the 5 months before it |
| `ANNUALE` | The current month and the 11 months before it |
| `STORICO` | Everything ever recorded |

`LOG` is the number of entries, `KILL/LOG` is average kills per entry, and `WIN/LOG` is average wins per entry.

### `l`: summaries by legend

```bash
python apex_stats.py l
```

This shows the same four periods for each legend you have played. Entries logged without a legend are grouped under `-`.

```
# LEGGENDA   | PERIODO      |    LOG |     KILL | VITTORIE | KILL/LOG | WIN/LOG
-------------------------------------------------------------------------------
Wraith       | MESE 2026-11 |      1 |        3 |        1 |     3.00 |    1.00
             | SEMESTRALE   |      3 |        9 |        3 |     3.00 |    1.00
             | ANNUALE      |      4 |       12 |        4 |     3.00 |    1.00
             | STORICO      |      5 |       15 |        5 |     3.00 |    1.00
-------------------------------------------------------------------------------
```

### `m`: current month totals

```bash
python apex_stats.py m
```

```
MESE 2026-11  |  KILL 15  |  VITTORIE 3
```

### `--dir`: custom data folder

`--dir` is a global option, so it goes **before** the command:

```bash
python apex_stats.py --dir D:/apex-backup add 5 1 --l octane
python apex_stats.py --dir D:/apex-backup report
```

This is handy for testing or for keeping separate profiles.

---

## How data is stored

```
apex_data/
├── apex_stats_2026-09.txt
├── apex_stats_2026-10.txt
└── apex_stats_2026-11.txt   ← current file (newest month)
```

Each monthly file has three sections:

1. **Header.** The totals of every earlier month, plus per-month and per-legend totals for the last 11 months. These carried-forward totals are what let the six-month, yearly and all-time summaries work without opening older files.
2. **Log.** One row per entry: date, legend, kills, wins. Rows are sorted by date.
3. **Summaries.** The `report` table, recalculated every time an entry is saved.

Example excerpt:

```
@FILE   | 2026-11
# TIPO  | RIFERIMENTO  |    LOG |     KILL | VITTORIE
--------------------------------------------------------------------------
@HIST   | < 2026-11    |     21 |       63 |       21
@PREV   | 2026-09      |      3 |        9 |        3
...
# LOG   | DATA             | LEGGENDA     | KILL | VITTORIE
--------------------------------------------------------------------------
L       | 2026-11-06 22:30 | Wraith       |    5 |        1
```

The tag at the start of each line (`@FILE`, `@HIST`, `@PREV`, `@HL`, `@PL`, `L`) tells the script what the line holds, so a file can be read in one quick pass. If you edit a file by hand, keep the tags, the `|` separators and the column order. A `|` typed in a legend name is saved as `/`.

---

## Privacy

Your logs are personal data. The included `.gitignore` keeps the `apex_data/` folder and all `apex_stats_*.txt` files out of git, so you can fork or contribute without publishing your match history.
