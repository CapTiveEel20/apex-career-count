# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

User-facing documentation lives in `README.md`. This file holds only the constraints for AI agents working on the code.

## STRICT CHAT RULE (from the user, applies to every interaction)

Whenever you use file-writing tools (Write, Edit, etc.), your chat reply must be exactly the single word `DONE`. Output nothing else: no summaries, diffs, explanations, or acknowledgement of this rule.

## System constraints

- **English only.** All code, identifiers, comments, terminal output, table headers, data-file labels and docs must be in English.
- **No external libraries.** Use only the Python standard library.
- **Keep I/O low.**
  - Every operation reads only the current (newest) monthly file, once. Never reopen older files.
  - Historical, semiannual, annual and level figures come from the totals carried forward in the current file's header (`@HIST`, `@PREV`, `@HL`, `@PL`, `@LV`).
  - Parsing stays O(1) per line: `load` dispatches on the constant prefix in the first `|`-separated column and stops at the `# SUMMARY` footer.
  - The only other file is `account_stats.txt`: the global account totals (`@ACCOUNT` line) and the legend bases (`@BASE | legend | kills | wins | updated` lines).
    - It is read by `load_acct` (returns `(account, bases)`; `load_account` returns just the account): by `report`, `l`, `k`, `w`, `account` and `base`, and when an entry with kills or wins is saved (`save_log`) or undone (`bump_account`).
    - `account_cmd` reads it once and passes the totals to `save_log` (`account=`), so they are not read twice.
    - It is written only through `write_acct` (via `write_atomic`), which always rewrites both the `@ACCOUNT` line and every `@BASE` line. `save_account` and `save_base` re-read the file first, so neither drops the other's data.
- **Write atomically.**
  - Every save goes through `write_atomic` (write to `.tmp`, then `os.replace`).
  - Each operation writes at most one monthly file. The only extra write is the account-totals update, which happens after the monthly file is written.
  - The only exception is `undo` emptying a month: it deletes that file (`os.remove`), so the untouched previous month becomes current again.
- **Output tables.**
  - Summary and report tables have no tag/`TAG` column, no per-entry average columns and **no `LOGS` column**. They start with the `REFERENCE` (or `LEGEND`/`PERIOD`) column and show only kills, wins and levels.
  - Report rows use `rep_cells`/`REP` (KILLS, WINS).
  - The `LOGS` aggregate (`AGG[0]`) still exists, but only in the file header lines (`@HIST`/`@PREV`/`@HL`/`@PL`). It is kept only for backward compatibility of the file format. Never display it.
- **Account totals (`account`).** There is no `sync` command (removed on purpose); `account` does that job.
  - `account` shows the saved global all-time totals.
  - `account <kills> <wins> [legend] [level]` (`account_cmd`):
    - First time (no totals yet): saves them. Nothing is logged; a legend or level is rejected.
    - Afterwards: logs `(new - saved)` as one match entry through `save_log` (sticky legend in the REPL, `--l`/`--date` on the CLI). `save_log` then moves the totals to the new values, and it prints an `ACCOUNT old -> new (+gain)` line before the `SAVED` line.
    - Equal totals and no level: nothing is logged. Any value lower than the saved one is a correction: the totals are replaced and nothing is logged.
  - They are dynamic once set:
    - `save_log` adds the entry's kills and wins, and flags the entry `acc = 1` (the `ACC` column, 7th field of the log record).
    - `undo` subtracts the removed entry's kills and wins only when `acc == 1` (`bump_account`), so entries logged before the totals were set never unbalance them.
    - This is a no-op for level-only (0/0) entries and while the totals have never been set.
    - The totals are clamped at 0.
    - Monthly rotation never moves them.
  - `account_line` displays them: `report` shows kills and wins at the top, `k` shows kills only, `w` shows wins only.
  - Malformed `account` input (one value, text, more than two values) raises `InputError`. Negative values keep a specific error.
- **Legend bases (`base`).**
  - `base <legend> <kills> <wins>` (`base_cmd`) takes the legend's **all-time** totals, like `account` does for the account. The legend is the tokens before the last two numbers, normalized with `clean`.
    - Legend not listed yet: the values become its all-time totals. Logged entries are included, never added on top: the stored `@BASE` is `typed - logged` (`legend_logged`, one read of the current file). Nothing is logged, so the account totals don't change.
    - Legend already listed: the gain `(typed - current all-time)` is logged as a match for that legend through `save_log` (so it reaches the account totals; `undo` reverses it). It prints a `BASE old -> new (+gain)` line first. Equal: nothing logged. Lower: a correction of the base, nothing logged.
    - Values below what is already logged for the legend are rejected. `0 0` removes the base. `base` lists the legends with a base and their all-time totals (`base_table`).
  - Setting or correcting a base never changes the account totals; only the logged gain does.
- **Aggregation.** Every match is counted in its legend's all-time totals and in the global account totals.
  - Legend all-time = base + logged entries (`@HL` + current logs), computed in `legend_periods(..., bases)`. `l` and the `ALL-TIME` column of `k`/`w` use it.
  - The account totals are bumped by `save_log` (see above). Both are reversed by `undo`.
- **`l` = one all-time table per legend** (`legend_report`, `LREP_HEAD`): LEGEND, KILLS, WINS, plus `GRAND TOTAL`. No time periods.
- **Quick entries: single tokens** (`save_quick`, REPL and CLI).
  - `<n>` = absolute level; `<n>l` (or the older `+<n>`) = n more levels (`QUICK_RE`/`LEVEL_RE`).
  - `<n>k` = n kills / 0 wins; `<n>w` = 0 kills / n wins (`QUICK_RE`). n must be at least 1. Nothing may follow them.
  - `<n>k` and `<n>w` never carry a legend: they bypass the sticky legend and don't change it.
- **Sticky legend (REPL only).**
  - `interactive` keeps `sticky`, the last legend typed in a match or `account` update. Matches and `account` updates that omit the legend use it.
  - A typed legend replaces it; `-` clears it. Quick entries (`<n>`, `<n>l`, `<n>k`, `<n>w`) never use it and never change it. The prompt shows it, e.g. `[Wraith]>` or `[2026-11-07 | Wraith]>`.
  - The CLI is stateless: no sticky legend.
- **Number format.**
  - All terminal numbers use thousands separators (`15,000`): tables via `num()` (`rep_cells`, `stat_report`, `lv_report`), and messages via `:,` (`fmt_saved`, `undo`, `account_cmd`, `base_cmd`, `m_text`, `account_line`, `check_level` errors).
  - Data files keep plain digits: `render` calls `summary(..., color=False, sep=False)`, and `write_acct` writes plain values.
  - Kills/wins input accepts separators (`NUM_RE`, `to_int`); level tokens do not.
- **Colors: raw ANSI codes only** (no colorama or other libraries).
  - Kills red (`\033[91m`), wins green (`\033[92m`).
  - Prose and headers go through `paint` (`KW_RE`); table values are wrapped cell by cell (`red`/`green`) after padding, so alignment is kept.
  - `init_color` enables colors only when stdout is a TTY and `NO_COLOR` is unset; on Windows it turns on VT mode via `ctypes`.
  - Data files are never colored: `render` calls `summary(..., color=False, sep=False)`.
  - `<n>k` / `<n>w` in the menus are colored by `color_quick` (`QUICK_TXT_RE`), since `paint` does not match them.
- **Input order: kills first, then wins.**
  - Match entries are `<kills> <wins> [legend] [level]` everywhere: `add`, `account` updates, the REPL, `QUICK_GUIDE`, `cheat_text` and the docs.
- **One save path.**
  - Every save, whether `add`, an `account` update, a quick entry, a bare level value or an interactive entry, goes through `save_log`.
  - Level-only updates are a single bare value: `700` (absolute) or `5l` / `+5` (relative), in the REPL or as `python apex_stats.py 700` / `5l`.
  - The `[level]` of a full entry follows the same rule, with or without a legend (`5 1 wraith 700`, `5 1 wraith +3`, `5 1 +3`).
    - `parse_extra` returns `(legend, level, delta)` via `level_arg`/`LVL_TOKEN_RE`.
    - No `+` means absolute (`delta=None`); `+<n>` means relative (`delta=n`, which must be at least 1).
  - They go through `save_level`, which wraps `save_log`, so the level check always runs. `+<n>` is resolved inside `save_log` (`delta`) as `last_level` before the entry's date plus `n`.
  - `lv` is report-only and never records a level. `add` always needs kills and wins.
  - Dates are parsed by `parse_when`, which accepts `YYYY-MM-DD` or `YYYY-MM-DD HH:MM`. Custom dates (`--date`, or the interactive `date` command) must apply to full entries and level-only entries alike.
- **Levels never decrease.**
  - The level is the absolute account level (0 = not recorded).
  - `check_level` rejects a level lower than the last one recorded before its date, or higher than one recorded after it.
  - `@LV` pruning (`prune_lv`) keeps one baseline day older than the 1-year window.
- **Success messages** come from `fmt_saved`: prefixed `SAVED`, with no entry counter. Level-only entries show only the level and the day (`SAVED - LEVEL 693 (2026-11-06)`).
- **`report` = match summary followed by the level report.**
  - Both come from the same single `load` of the current file. `report_text` calls `summary` and then `lv_report`; `lv` uses the same `lv_report`.
  - `lv_report` uses each current-month entry's level, not just per-day maximums, so gains within a single day are counted.
- **`l`, `k` and `w` list only real legends.**
  - Entries with no legend (`NO_LEGEND` `-`, e.g. level-only updates) are excluded. All three are built from `legend_periods`.
  - `k` and `w` (`stat_report`) show a single statistic, kills or wins, per legend: month, semiannual, annual and the all-time total.
  - They end with a `GRAND TOTAL` row: the sum over the listed legends for every column, so its `ALL-TIME` is the absolute historical total.
- **There is no `logs` command** (it was removed on purpose). Don't add an entry-count command or column.
- **The REPL exits only on an empty input line.** There is no `q` command. EOF and Ctrl+C just stop the loop safely.
- **There is no `help` command** (removed on purpose).
  - `c` (`cheat_text(cli)`) is the only explanation screen. Keep it in sync with the input formats and commands.
- **REPL quick guide.**
  - `QUICK_GUIDE` is printed when the REPL starts.
    - Exact text: the `APEX STATS TRACKER` banner, then `[ SETUP ]` (account, always first), `[ BASE ]`, `[ MATCH ]`, `[ QUICK ]` (`<n>k | <n>w`), `[ LEVEL ]` (`<n> | <n>l`), `[ REPORT ]`, `[ TOOLS ]` and `[ LEGEND ]` (sticky legend) rows, a dashed line, and "Press Enter on an empty line to quit." No line is wider than `MENU_W` (79).
    - Print it through `quick_guide()`: `paint`, a red `k` and a green `w`, plus `color_quick`.
  - `cheat_text` reuses the same banner (`MENU_TITLE`, `MENU_W` wide) and `[ SECTION ]` layout, adding a description per command and a `[ RULES ]` block. The sticky-legend rule appears only in the REPL version (`cli=False`).
  - It is also the fallback for any unrecognized or malformed input: raise `InputError` and the loop prints it.
  - Well-formed input that breaks a rule (level check, closed month, negative values) keeps its specific error message.
- **Undo is a LIFO stack by entry `ID`** (the order entries were added in), not by date.
- **Stay backward-compatible.** `L` lines without the level, `ID` or `ACC` columns must still load.
  - A missing level counts as 0.
  - A missing `ID` is the line's position in the file.
  - A missing `ACC` counts as 0 (not added to the account totals).
