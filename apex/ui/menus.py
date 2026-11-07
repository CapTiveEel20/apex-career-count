"""The REPL quick guide (QUICK_GUIDE) and the 'c' cheat sheet, which share one banner and layout."""
from apex.display.colors import color_quick, green, orange, paint, red

MENU_W = 79
QUICK_GUIDE = (
    "\n===============================================================================\n"
    "                              APEX STATS TRACKER\n"
    "===============================================================================\n"
    " [ SETUP ]   account <kills> <wins> (1st: saves totals; later: logs new - old)\n"
    " [ BASE ]    base <legend> <kills> <wins> (1st: sets total; later: logs gain)\n"
    " [ MATCH ]   <kills> <wins> [legend] | <kills> <legend> (1 win; e.g. 5 wraith)\n"
    " [ QUICK ]   <n>k | <n>w (n kills | n wins; pinned legend if any; e.g. 5k | 1w)\n"
    " [ LEVEL ]   <n> | <n>l (e.g. 500 or 5l)\n"
    " [ REPORT ]  report | m | l | lv | k | w | log | logl\n"
    " [ TOOLS ]   undo | date YYYY-MM-DD | date today | c (help)\n"
    ' [ LEGEND ]  p: sticky ON/OFF (ON pins the legend you type; "-" unpins + OFF)\n'
    "-------------------------------------------------------------------------------\n"
    " Press Enter on an empty line to quit.\n"
)
MENU_TITLE = QUICK_GUIDE[:QUICK_GUIDE.index(" [ SETUP ]")]  # shared banner: QUICK_GUIDE and cheat_text


def quick_guide():
    """QUICK_GUIDE for the terminal: kill words, the k command and <n>k red; win words, w and <n>w green;
    orange only for the lv command and the [ LEVEL ] inputs and examples (the tag stays plain)."""
    return color_quick(paint(QUICK_GUIDE).replace(
        "| l | lv | k | w |", f"| l | {orange('lv')} | {red('k')} | {green('w')} |").replace(
        "<n> | <n>l (e.g. 500 or 5l)\n",
        f"{orange('<n>')} | {orange('<n>l')} (e.g. {orange('500')} or {orange('5l')})\n"))


def cheat_text(cli):
    """Full cheat sheet in the same layout as QUICK_GUIDE (title, [ SECTION ] rows, footer).
    cli=True for the command line, False for the interactive prompt."""
    a = "add " if cli else ""
    lvl = "python apex_stats.py " if cli else ""
    sections = (
        ("SETUP", (("account <kills> <wins>", "1st time: save your all-time totals (e.g. account 15000 800)"),
                   ("account <kills> <wins>", "later: log the gain (new - saved), kills and wins only"),
                   ("account", "show the saved global account totals"))),
        ("BASE", (("base <legend> <kills> <wins>", "1st time: set a legend's all-time totals (e.g. base wraith 3000 120)"),
                  ("base <legend> <kills> <wins>", "later: log the gain (new - current) as a match for it"),
                  ("base", "list the legends with a base and their all-time totals"))),
        ("MATCH", ((f"{a}<kills> <wins> [legend]", "save a match (e.g. 5 1 wraith | 5 1)"),
                   (f"{a}<kills> <legend>", "save a match with 1 win (e.g. 5 wraith = 5 kills, 1 win)"))),
        ("QUICK", ((f"{lvl}<n>k", "n kills only: 0 wins, no legend (e.g. 5k)" if cli else
                    "n kills only: 0 wins, pinned legend if any (e.g. 5k)"),
                   (f"{lvl}<n>w", "n wins only: 0 kills, no legend (e.g. 1w)" if cli else
                    "n wins only: 0 kills, pinned legend if any (e.g. 1w)"))),
        ("LEVEL", ((f"{lvl}<n>", "set your absolute level (e.g. 700)"),
                   (f"{lvl}<n>l", "add n to the current level (e.g. 3l; +3 works too)"))),
        ("REPORT", (("report", "account totals + match summaries + level report"),
                    ("m", "kills and wins this month"),
                    ("l", "base legends' all-time kills and wins + top 3 by kills this month"),
                    ("lv", "levels gained (1 week ... 1 year)"),
                    ("k", "account kills + kills per legend (+ grand total)"),
                    ("w", "account wins + wins per legend (+ grand total)"),
                    ("log", "this month's matches (account and base updates excluded)"),
                    ("logl", "level history (this month + earlier days)"))),
        ("TOOLS", (("undo", "remove the last entry, base or account change (repeatable)"),
                   (('--date "YYYY-MM-DD[ HH:MM]"', "date for add, account, base and quick entries") if cli else
                    ("date YYYY-MM-DD", "use this date for the next entries")),
                   *((() if cli else (("date today", "back to the system date"),))),
                   ("c", "this cheat sheet (help)"))),
        *((() if cli else (("LEGEND", (("p", "sticky legend ON/OFF (OFF by default)"),
                                       ("-", "unpin the legend and turn sticky OFF"))),))),
    )
    w = max(len(c) for _, rows in sections for c, _ in rows) + 2
    out = [MENU_TITLE.rstrip("\n")]
    for tag, rows in sections:
        for i, (c, d) in enumerate(rows):
            if tag == "LEVEL":  # <n> / <n>l orange, any "python apex_stats.py " prefix plain
                cell = c[:len(lvl)] + orange(c[len(lvl):]) + " " * (w - len(c))
            else:  # k red, w green, lv orange
                cell = {"k": red, "w": green, "lv": orange}.get(c, str)(c) + " " * (w - len(c))
            out.append(f" {'[ ' + tag + ' ]' if i == 0 else '':<10}  {cell}{d}")
    out += ["-" * MENU_W,
            " [ RULES ]   - Kills first, then wins, then an optional legend. Matches take no level.",
            "               <kills> <legend> (one number, then a legend) counts as 1 win.",
            "             - Legends are saved capitalized (wraith -> Wraith).",
            "             - Every match adds its kills and wins to its legend's all-time totals",
            "               (base + logged: l, k, w) and to the global account totals.",
            "             - account: kills and wins only. The 1st time saves your totals; later it logs",
            "               (new - saved). Lower values are an error: nothing changes. undo takes it back out.",
            "             - base: the 1st time sets the legend's all-time totals (logged entries",
            "               included, nothing logged); later it logs (new - current) for that legend.",
            "               undo also reverts a base you set, corrected or removed.",
            "             - Level <n> = absolute (never lower than the last one); <n>l adds n to it.",
            "               SAVED lines of matches show your current account level.",
            "             - <n>k and <n>w never use a legend." if cli else
            "             - <n>k and <n>w use the pinned legend, if any (no legend otherwise).",
            "             - Entries cannot be dated in a month older than the newest data file.",
            "             - Numbers are shown with thousands separators (15,000); kills/wins may be typed so."]
    if not cli:
        out += ['             - Sticky legend: OFF by default; "p" turns it ON/OFF. While ON, the legend you',
                '               type is pinned and reused by matches without one and by <n>k / <n>w,',
                '               until you type another one. "-" unpins it and turns sticky OFF.']
    out += ["-" * MENU_W,
            " Run with no arguments for interactive mode." if cli else " Press Enter on an empty line to quit."]
    return color_quick(paint("\n".join(out) + "\n"))
