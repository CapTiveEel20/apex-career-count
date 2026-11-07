# CLAUDE.md (AI SYSTEM DIRECTIVES)
This file holds strict constraints for AI agents. Do not read other workspace files unless explicitly requested.

## 0. STRICT CHAT & EFFICIENCY RULES (CRITICAL)
1. **NO YAPPING:** When using file-writing tools, reply with EXACTLY the single word `DONE`. No summaries, no diffs, no step-by-step explanations, no apologies.
2. **TARGETED EDITS ONLY:** NEVER rewrite or output the entire `apex_stats.py` file. Only output/edit the specific functions or lines that need changing.
3. **ENGLISH ONLY:** All code, variables, comments, terminal output, and file data MUST be in English.

## 1. ARCHITECTURE & STATE
- **Layers (Import downward only):** `config` → `core` → `display` → `storage` → `services` → `ui` → `cli`.
- **Colors:** Managed strictly in `apex.display.colors`. Use `red` (kills), `green` (wins), `orange` (levels: `\033[38;5;208m`). Never import `COLOR` boolean directly. Data files must remain uncolored. Use comma separators (`1,500`) in UI, plain digits in data files.
- **Data Files:** Atomic writes via `storage/atomic.py`. Read current month once. `account_stats.txt` holds `@ACCOUNT` and `@BASE`.
- **Log Record:** `L | DATE | LEGEND | KILLS | WINS | LEVEL | ID | ACC | SRC`. `ACC=1` = added to the account totals (NOT "from `account`"). `SRC` = origin: `M` match/quick, `A` account gain, `B` base gain, `L` level update (`save_log(source=...)`). Files without `SRC` still load: level-only = `L`, the rest = `M`.
- **REPL State:** Exits only on empty Enter (no `q`). No `help` or `logs` commands (`log`/`logl` exist). Sticky legend (REPL only) is OFF by default; `p` toggles it ON/OFF (OFF also unpins). While ON, a legend typed in a match is pinned and applies to matches without a legend AND to `<n>k` / `<n>w` without one (`save_quick(..., legend)`). A typed `-` legend, or `-` alone on a line (saves nothing), unpins it and turns it OFF. Level entries (`<n>`, `<n>l`) never take a legend.

## 2. COMMAND LOGIC
- **Input Order:** matches are `<kills> <wins> [legend]` or `<kills> <legend>` (`parse_match`). Kills always first. `<kills> <legend>` (1 number, then a legend) = wins 1; two numbers are always kills and wins (no win added). Matches take NO level (`parse_legend` rejects any number after kills/wins); levels come only from `<n>` / `<n>l`.
- **Account (`account <k> <w>`):** Kills and wins only: no legend, no level, no `--l`, no sticky legend. Sets global totals. If totals exist, logs diff as an entry with no legend (`SRC=A`). Lower values are an error: the update is aborted, saved totals kept, nothing logged. Every `ACCOUNT` line shows the current level (`account_line(..., level=)`, `level_txt`: word and number orange).
- **Base (`base <legend> <k> <w>`):** Legend, kills and wins only. Sets legend all-time totals. If exists, logs diff (`SRC=B`). Lower values trigger a silent correction. Discard input if lower than already logged values.
- **Quick (`<n>k [legend]` / `<n>w [legend]`):** `parse_quick`. A legend typed after them is used as is, bypassing the sticky legend (which stays pinned/unchanged); without one they take the pinned legend, if any.
- **Levels (`<n>` or `<n>l`):** `<n>` is absolute, `<n>l` or `+<n>` is relative. Handled via `save_level`. Levels can NEVER decrease.
- **SAVED line:** matches (and quick `<n>k`/`<n>w`, account and base gains) show the current account level (latest recorded, returned by `save_log` as its 3rd value) via `fmt_saved(rec, level)`; `LEVEL -` if none. Order follows input: `SAVED  <legend>  KILLS <k>  WINS <w>  LEVEL <n>  (<date>)`.
- **Undo:** LIFO by `ID`. Reverts `L` (match), `@BU` (base change) and account changes. Account changes are `@BU` lines with legend `@ACCOUNT` (`ACC_TAG`) holding the previous `@ACCOUNT` (k, w, updated; `-` = never set): the first save writes one (`record_account`), an account gain writes one with the SAME `ID` as its `SRC=A` entry (`save_log`); undo removes both together and restores the old totals exactly (`restore_account`). Old `SRC=A` entries without a snapshot fall back to subtracting the gain. If `base` is undone, correctly reverts base stats without data corruption. After every undo, prints `Latest entry now:` with the remaining log entry of highest `ID` (`none` if the file has none).

## 3. REPORTING & UI LAYOUT
- **Quick Guide / `c`:** Strict layout order: `[ SETUP ]`, `[ BASE ]`, `[ MATCH ]`, `[ QUICK ]`, `[ LEVEL ]`, `[ REPORT ]`, `[ TOOLS ]`, `[ LEGEND ]`. Max 79 chars.
- **Report Menu Order:** `report | m | l | lv | k | w | log | logl` (`lv` colored orange).
- **`log`:** current file's `SRC=M` entries only (account/base gains and level updates excluded). **`logl`:** level history: carried `@LV` days + current-file entries with a level, with the change from the previous row. Both read only the current file.
- **Level Menu Line:** `[ LEVEL ]   <n> | <n>l (e.g. 500 or 5l)`: `<n>`, `<n>l`, `500`, `5l` orange; the `[ LEVEL ]` tag plain.
- **`report`:** Shows match summary followed by level report.
- **`m`:** Current month kills/wins, then `TOP 5 ALL-TIME HIGHEST KILL MATCHES` (`top_matches`): `SRC=M` entries with kills > 0, ties = earlier first. Carried across months in the `@TK` header (top 5 of previous months).
- **`l` (Legends):** 2-columns (Side-by-side). Left: Legends initialized via `base`, sorted by all-time KILLS descending, with the date and time (YYYY-MM-DD HH:MM) of each one's last logged match (`LAST MATCH`, `-` if none; `SRC=M` entries only, carried across months in the `@LL` header) (NO grand totals). Right: "TOP 3 THIS MONTH" by kills.
- **`k` / `w`:** List real legends only. Show month, semiannual, annual, all-time. Ends with `GRAND TOTAL` row.
- **Levels UI:** Apply ANSI Orange ONLY to specific level variables/outputs (e.g., the 3rd column "GAINED" header word and values, current level number, and error numbers).