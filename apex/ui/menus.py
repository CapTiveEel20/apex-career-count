"""The help menu (QUICK_GUIDE): shown by 'c', when the REPL starts and on unrecognized input."""
from apex.display.colors import color_quick, orange, paint

QUICK_GUIDE = (
    "\n===============================================================================\n"
    "                           APEX STATS TRACKER\n"
    "===============================================================================\n"
    " [ ACCOUNT ] account <k> <w> [lvl] (Sets/Syncs totals) | accountl <lvl> (Level)\n"
    " [ BASE ]    base <name> <k> <w> (Sets/Syncs legend totals)\n"
    " [ STICKY ]  p <name> (Lock) | 7 (7k, 0w) | 7 1 (7k, 1w) | - (Unlock)\n"
    " [ MATCH ]   <k> <w> <legend> | <n>k (e.g. 5k wraith) | <n>w | <n>l (Add levels)\n"
    " [ TABLES ]  l (Kills) | lw (Wins) | la (A-Z) | lm (Recent) | ls <name> (Search)\n"
    " [ SYSTEM ]  report | undo | date YYYY-MM-DD | date today | c (help)\n"
    "-------------------------------------------------------------------------------\n"
)


def quick_guide():
    """QUICK_GUIDE for the terminal: kill words and <n>k red; win words and <n>w green;
    orange only for the level inputs."""
    text = paint(QUICK_GUIDE)
    for level_input in ("[lvl]", "accountl <lvl>", "<n>l"):
        text = text.replace(level_input, orange(level_input))
    return color_quick(text)
