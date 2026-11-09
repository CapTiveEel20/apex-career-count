# CLAUDE.md (AI SYSTEM DIRECTIVES)
This file holds strict constraints for AI agents. Do not read other workspace files unless explicitly requested.

## 0. STRICT CHAT & EFFICIENCY RULES (CRITICAL)
1. **NO YAPPING:** When using file-writing tools, reply with EXACTLY the single word `DONE`. No summaries, no diffs, no step-by-step explanations, no apologies.
2. **TARGETED EDITS ONLY:** NEVER rewrite or output the entire `apex_career_count.py` file. Only output/edit the specific functions or lines that need changing.
3. **ENGLISH ONLY:** All code, variables, comments, terminal output, and file data MUST be in English.

## 1. COMMANDS
```bash
python apex_career_count.py                                            # run (no command-line arguments)
python -m unittest                                                     # tests, from the repo root
python -m PyInstaller --noconfirm --distpath . apex_career_count.spec  # rebuild apex_career_count.exe next to apex_data/
```
- **Tests:** standard library only, temporary folders, in `tests/`. Drive commands through `Session.handle` (`tests/helpers.py`: `SessionCase`). Use dates in the past: future days are refused.
- **Rebuild the `.exe` after a data-format change:** an older build drops header rows it does not know when it saves.

## 2. ARCHITECTURE
Standard library only. **Layers (import downward only):** `config` → `core` → `display` → `storage` → `services` → `ui`.

| Package | Modules |
|---|---|
| `apex/core` | `records` (typed records), `parsing`, `aggregates`, `levels`, `totals` (no I/O) |
| `apex/display` | `colors`, `tables`, `messages` |
| `apex/storage` | `ledger`, `monthly_file`, `account_file`, `atomic` |
| `apex/services` | `entries`, `account`, `bases` |
| `apex/ui` | `repl` (`Session`), `reports` (read-only views, `VIEWS`), `menus` |

- **Records:** typed in `core/records.py` (`Tally`, `Stored`, `TopMatch`, `LevelDay`, `Periods`, `LegendRow`, `MatchTotals`, `Entry`, `Change`, `Month`). Use named fields, never positional indexes.
- **Colors:** managed strictly in `apex.display.colors`. Never import the `COLOR` boolean directly. `red` = kills, `green` = wins, `orange` (`\033[38;5;208m`) = levels. `cyan` / `purple` (`\033[38;5;93m`) / `blue` are for category tags only, everywhere (menu, `help`, undo, `TOTALS`): `[ACCOUNT...]` purple, `[MATCH]` cyan, `[BASE...]` blue.
- **Numbers:** comma separators (`1,500`) in the UI, plain digits in data files. Data files are never colored.

## 3. DATA FILES
- **Access:** commands read and write both data files only through `Ledger` (`storage/ledger.py`): each file read at most once, one all-or-nothing commit (month file first) when its `with` block ends. Read-only views in `ui/reports.py` use `load_current` / `load_acct`. Atomic writes via `storage/atomic.py`.
- **`account_stats.txt`:** `@ACCOUNT` and `@BASE`.
- **Monthly files (`apex_stats_YYYY-MM.txt`):** read the current month once. Headers carry earlier months forward: `@HIST`, `@PREV`, `@HL`, `@PL`, `@LV`, `@LL` (last match per legend), `@TK` (Top 5 matches), `@MB` (monthly bests). `@BU` = undo records (`Change`).
- **Damaged lines:** a line that cannot be read is skipped with a stderr warning (`read_month`, `load_acct`) and kept in its file as `@BAD`, so a later save does not lose it. A damaged `@ACCOUNT` line blocks every `Ledger` use of the account file with an error until fixed by hand.
- **Log record:** `L | DATE | LEGEND | KILLS | WINS | LEVEL | ID | ACC | SRC`.
  - `ACC=1` = added to the account totals (NOT "from `account`").
  - `SRC` = origin: `M` match/quick, `A` account gain, `B` base gain, `L` level update (`record_gain(source=...)` for `M`/`A`/`B`, `record_level` for `L`).
  - Files without `SRC` still load: level-only = `L`, the rest = `M`.
- **`SRC=A` / `SRC=B` entries are never single matches:** excluded from `log`, the Top 5 (`@TK`), `@MB`, `g` and `LAST MATCH` (`@LL`).

## 4. REPL
- Always starts `interactive()`. Exits only on empty Enter (no `q`). No `logs` command (`log` exists). No `m`, `lv` or `lk` command.
- Unrecognized input shows the main menu. A data file that cannot be read answers with an error; the session goes on.
- `date <day>` rejects future days (the active date stays). A record dated before the newest file's month is refused (closed month).
- **Sticky legend:** OFF by default. `p <name>` locks a legend set with `base` (missing/unknown name: error, nothing changes). The locked legend applies to matches without a legend AND to `<n>k` / `<n>w` without one (`save_quick(..., legend)`). While it is locked, a number alone = wins 1, the same as `<kills> <legend>` (`parse_match(..., pinned=)`); `<kills> 0` saves no win. A legend typed in an entry is used instead (Legend Resolution) and leaves the lock unchanged. A typed `-` legend (matches and quick entries), or `-` alone on a line (saves nothing), unpins it and turns it OFF. Level entries (`<n>l`, `accountl <n>`) never take a legend.

## 5. COMMAND LOGIC
- **Matches:** `<kills>`, `<kills> <wins> [legend]` or `<kills> <legend>` (`parse_match`). Kills always first. A number alone = kills, wins 0; with a sticky legend locked it counts like `<kills> <legend>` (wins 1). `<kills> <legend>` (1 number, then a legend) = wins 1. Two numbers are always kills and wins (no win added). Matches take NO level (`parse_legend` rejects any number after kills/wins); levels come only from `<n>l` / `accountl <n>`.
- **Quick (`<n>k [legend]` / `<n>w [legend]`):** `parse_quick`. A typed legend bypasses the sticky legend; without one they take the pinned legend, if any. Anything after `<n>l` is an error.
- **Legend Resolution:** matches and quick `<n>k`/`<n>w` go through `_match_legend` (`resolve_legend`), any case, against the known legends (`@BASE` + logged legends). Exact match wins, then a single prefix match; several prefix matches = error, nothing saved. An unknown name asks `Unknown legend '<name>'. Create new? (y/n):` (`confirm_new_legend`); only `y` proceeds, else `ValueError(ABORTED)`. `base` and `p` do not use it. A number among the legend tokens is an error message in every entry format, never the menu.
- **Shared Totals Decision:** `account` and `base` both classify typed totals with `decide_totals` (`core/totals.py`): `FIRST`, `LOWERED`, `UNCHANGED` or `GAINED`.
- **Downgrade Protection:** `account`, `base` (`0 0` removal included; both through `decide_totals`) and `accountl` call `confirm()` (`confirm_lower`) before lowering a value below the current one. Prompt: `Warning: New value is lower than current. Proceed? (y/n):`. Only `y` proceeds; anything else raises `ValueError(ABORTED)` and changes nothing.
- **Account (`account <k> <w> [lvl]`):** no legend, no sticky legend. Sets global totals; `lvl` also records the account level (a level entry saved first; equal level logs nothing). One confirmation covers the whole command, asked if the level or the totals would go down. If totals exist, logs the diff as an entry with no legend (`SRC=A`). Lower values, once confirmed, replace the totals with a `@BU` undo record and nothing logged. Every `ACCOUNT` line shows the current level (`account_line(..., level=)`, `level_txt`: word and number orange).
- **Base (`base <legend> <k> <w>`):** legend, kills and wins only. Sets legend all-time totals. A gain (typed > current all-time totals) is logged through `record_gain` as an `L` entry for that legend (`SRC=B`): it shows in `report` and bumps `@ACCOUNT` (like `account`); undo removes it. A first set, a correction (lower values) or a removal (`0 0`) logs NO entry (only an `@BU` undo record, `Ledger.change_base` / `Ledger.remove_base`). A stored base of `0 0` is valid (logged entries cover the totals); only a typed `0 0` removes. Discard input lower than already logged values.
- **Levels (`<n>l` or `accountl <n>`):** `<n>l` is relative (`save_quick`), `accountl <n>` is absolute (`accountl_cmd`). All are saved by `record_level`, whose callers confirm any lowering first. A level decreases only through a confirmed `accountl`, so the current level is the most recently recorded one (`latest_level`), not the highest.
- **Top 5 Matches:** all-time leaderboard of single matches by kills (`top_matches`, `TOP_MATCHES = 5`): `SRC=M` entries with kills > 0 (quick `<n>k` included), ties = earlier first. Derived from the carried `@TK` rows + the current file, so undo needs no extra step; `roll_over` stores the new top 5 in `@TK`. Kept in the data files; no command shows it.
- **SAVED line:** matches (and quick `<n>k`/`<n>w`, account and base gains) show the current account level (latest recorded, `Saved.level`) via `fmt_saved(rec, level)`; `LEVEL -` if none. Order follows input: `SAVED  <legend>  KILLS <k>  WINS <w>  LEVEL <n>  (<date>)`.
- **Undo:** LIFO by `ID`. Reverts `L` (match), `@BU` (base change) and account changes, without data corruption.
  - Account changes are `@BU` lines with legend `@ACCOUNT` (`ACC_TAG`) holding the previous `@ACCOUNT` (k, w, updated; `-` = never set). The first save or a confirmed lowering writes one (`Ledger.change_account`). An account gain writes one with the SAME `ID` as its `SRC=A` entry (`Ledger.add`); undo removes both together and restores the old totals exactly (`Ledger.revert_last`). Old `SRC=A` entries without a snapshot fall back to subtracting the gain.
  - After every undo, prints `PREVIOUS LOG:` with the remaining action of highest `ID` (`Month.last_action()`, what the next undo reverts; `fmt_previous`), labeled `[MATCH]` (cyan), `[ACCOUNT UPDATE]` (purple: `SRC=A` entry or account `@BU`), `[BASE UPDATE]` (blue: `SRC=B` entry or base `@BU`) or `[LEVEL UPDATE]` (orange); `none` if nothing is left. In it the whole `KILLS <n>` is red and the whole `WINS <n>` green (`kw_values`), e.g. `Legend: Rampart | KILLS +8 | WINS +0`.

## 6. REPORTING & UI LAYOUT
- **Main Menu (`quick_guide`):** shown at REPL start and on unrecognized input. Strict layout order (`help` too): `[ ACCOUNT ]`, `[ BASE ]`, `[ MATCH ]`, `[ STICKY ]`, `[ TABLES ]`, `[ SYSTEM ]`. In `[ TABLES ]`: the `l` commands, then `g`, then `k | w`.
- **Help:** `help` prints a dedicated screen (`help_text`) explaining each command; it does not reprint the main menu.
- **Menu Colors:** kills red, wins green, levels orange (`[lvl]`, `<lvl>`, `<n>l`), every command `steel` (soft blue), title `yellow`, explanations and the other `[ TAG ]`s `gray`; borders and `<name>` / `<legend>` default.
- **Levels UI:** apply ANSI Orange ONLY to specific level variables/outputs (e.g. the 3rd column "GAINED" header word and values, current level number, and error numbers).
- **`l` (Legends):** two columns, side by side.
  - Left: legends initialized via `base`, sorted by all-time KILLS descending, with the date and time (YYYY-MM-DD HH:MM) of each one's last logged match (`LAST MATCH`, `-` if none; `SRC=M` entries only, carried across months in `@LL`). NO grand totals.
  - Right: "TOP 3 THIS MONTH" by kills (never filtered).
  - Variants (one word, no space; `legend_text(d, sort, search)`, `L_SORTS`): `l` = by kills, `lw` = by wins, `la` = by name, `lm` = by last match (most recent first, never played at the bottom), `ls <name>` = left column filtered by name (case-insensitive substring, by kills). The old `l a` / `l w` / `l s` forms no longer exist.
- **`g` (Top Games):** two side-by-side tables (`games_text`). Win `W` green / `L` red, kills red, legends in the default color.
  - Left: current month's top 10 (`TOP_GAMES`, `top_matches` over the file's logs: same rules as Top 5, wins never affect rank), derived, so undo needs no extra step.
  - Right: all-time top 6 monthly bests (`TOP_MONTH_BESTS`, `monthly_bests`, `@MB`): `roll_over` adds each closed month's #1 if there is room or its kills beat the lowest row.
  - If the newest file is from an earlier month, `g` shows that month as closed without writing anything.
- **`k` / `w`:** list real legends only. Show month, semiannual, annual, all-time. End with a `GRAND TOTAL` row.
- **`report`:** two side-by-side tables over the same `WINDOWS` (7, 30, 90, 180 and 365 days). Left `# SUMMARY` (`period_summary`: `PERIOD | FROM | KILLS | WINS`, one row per window + `ALL-TIME`). Right `LEVELS GAINED` (`levels_gained`, one row per window + `ALL-TIME`: current level minus the first level ever recorded, `first_level`; 0 if none). Windows count entries after `FROM` up to today; the older monthly files are read too (`older_logs`). Rows are 87 columns; the title line runs longer (about 110).
- **`log`:** two side-by-side tables within 79 columns, `LOG_RECENT` (20) rows each, oldest first. Left: current file's `SRC=M` entries only, with `WIN` shown as in `g` (`win_cell`: `W` green / `L` red). Right: carried `@LV` days + current-file entries with a level, with the change from the previous level. Reads only the current file.
