"""The REPL quick guide (QUICK_GUIDE) and the 'c' cheat sheet, which share one banner and layout."""
from apex.display.colors import color_quick, green, paint, red

MENU_W = 79
QUICK_GUIDE = (
    "\n===============================================================================\n"
    "                              APEX STATS TRACKER\n"
    "===============================================================================\n"
    " [ SETUP ]   account <kills> <wins> (1st: saves totals; later: logs new - old)\n"
    " [ BASE ]    base <legend> <kills> <wins> (1st: sets total; later: logs gain)\n"
    " [ MATCH ]   <kills> <wins> [legend] [level] (e.g. 5 1 wraith 57 | 5 1 57)\n"
    " [ QUICK ]   <n>k | <n>w (kills only | wins only, no legend; e.g. 5k | 1w)\n"
    " [ LEVEL ]   <n> | <n>l (e.g. 700 sets level 700 | 3l adds 3 levels)\n"
    " [ REPORT ]  report | l | k | w | m | lv\n"
    " [ TOOLS ]   undo | date YYYY-MM-DD | date today | c (help)\n"
    ' [ LEGEND ]  sticky: the last legend typed is reused by matches ("-" clears)\n'
    "-------------------------------------------------------------------------------\n"
    " Press Enter on an empty line to quit.\n"
)
MENU_TITLE = QUICK_GUIDE[:QUICK_GUIDE.index(" [ SETUP ]")]  # shared banner: QUICK_GUIDE and cheat_text


def quick_guide():
    """QUICK_GUIDE for the terminal: kill words, the k command and <n>k red; win words, w and <n>w green."""
    return color_quick(paint(QUICK_GUIDE).replace("| k | w |", f"| {red('k')} | {green('w')} |"))


def cheat_text(cli):
    """Full cheat sheet in the same layout as QUICK_GUIDE (title, [ SECTION ] rows, footer).
    cli=True for the command line, False for the interactive prompt."""
    a = "add " if cli else ""
    lvl = "python apex_stats.py " if cli else ""
    sections = (
        ("SETUP", (("account <kills> <wins>", "1st time: save your all-time totals (e.g. account 15000 800)"),
                   ("account <kills> <wins> [legend] [level]", "later: log the gain (new - saved) as a match"),
                   ("account", "show the saved global account totals"))),
        ("BASE", (("base <legend> <kills> <wins>", "1st time: set a legend's all-time totals (e.g. base wraith 3000 120)"),
                  ("base <legend> <kills> <wins>", "later: log the gain (new - current) as a match for it"),
                  ("base", "list the legends with a base and their all-time totals"))),
        ("MATCH", ((f"{a}<kills> <wins> [legend] [level]", "save a match (e.g. 5 1 wraith 57 | 5 1 57)"),
                   (f"{a}<kills> <wins> [legend] +<n>", "match + n levels (e.g. 5 1 wraith +3 | 5 1 +3)"))),
        ("QUICK", ((f"{lvl}<n>k", "n kills only: 0 wins, no legend (e.g. 5k)"),
                   (f"{lvl}<n>w", "n wins only: 0 kills, no legend (e.g. 1w)"))),
        ("LEVEL", ((f"{lvl}<n>", "set your absolute level (e.g. 700)"),
                   (f"{lvl}<n>l", "add n to the current level (e.g. 3l; +3 works too)"))),
        ("REPORT", (("report", "account totals + match summaries + level report"),
                    ("l", "all-time kills and wins per legend (base + logged)"),
                    ("k", "account kills + kills per legend (+ grand total)"),
                    ("w", "account wins + wins per legend (+ grand total)"),
                    ("m", "kills and wins this month"),
                    ("lv", "levels gained (1 week ... 1 year)"))),
        ("TOOLS", (("undo", "remove the last entry (repeatable)"),
                   (('--date "YYYY-MM-DD[ HH:MM]"', "date for add, account, base and quick entries") if cli else
                    ("date YYYY-MM-DD", "use this date for the next entries")),
                   *((() if cli else (("date today", "back to the system date"),))),
                   ("c", "this cheat sheet (help)"))),
    )
    w = max(len(c) for _, rows in sections for c, _ in rows) + 2
    out = [MENU_TITLE.rstrip("\n")]
    for tag, rows in sections:
        for i, (c, d) in enumerate(rows):
            cell = {"k": red, "w": green}.get(c, str)(c) + " " * (w - len(c))  # k red, w green
            out.append(f" {'[ ' + tag + ' ]' if i == 0 else '':<10}  {cell}{d}")
    out += ["-" * MENU_W,
            " [ RULES ]   - Kills first, then wins; a numeric 3rd value is the level, text is the legend.",
            "             - Legends are saved capitalized (wraith -> Wraith).",
            "             - Every match adds its kills and wins to its legend's all-time totals",
            "               (base + logged: l, k, w) and to the global account totals.",
            "             - account: the 1st time saves your totals; later it logs (new - saved) as a",
            "               match. Lower values only correct the totals. undo takes a match back out.",
            "             - base: the 1st time sets the legend's all-time totals (logged entries",
            "               included, nothing logged); later it logs (new - current) for that legend.",
            "             - Level <n> = absolute (never lower than the last one); <n>l adds n to it.",
            "             - <n>k and <n>w never use a legend.",
            "             - Entries cannot be dated in a month older than the newest data file.",
            "             - Numbers are shown with thousands separators (15,000); kills/wins may be typed so."]
    if not cli:
        out += ['             - Sticky legend: a legend you type is reused by later matches and account',
                '               entries that omit it, until you type another one ("-" clears it).']
    out += ["-" * MENU_W,
            " Run with no arguments for interactive mode." if cli else " Press Enter on an empty line to quit."]
    return color_quick(paint("\n".join(out) + "\n"))
