"""The main menu (quick_guide: when the REPL starts and on unrecognized input) and the 'help' screen."""
from apex.display.colors import blue, cyan, gray, green, orange, purple, red, steel, visible_len, yellow

HELP_CMD_W = 23  # visible width of the command column of the help screen


def quick_guide():
    """The main menu: kills red, wins green, levels orange, commands soft blue, title yellow,
    [ ACCOUNT ] purple, [ BASE ] blue, [ MATCH ] cyan, other tags and explanations gray;
    borders and names in the default color. Plain text when colors are off."""
    k, w, lvl = red("<k>"), green("<w>"), orange("<lvl>")
    cmd, note = steel, gray
    equals, dashes = "=" * 79, "-" * 79
    return (
        f"\n{equals}\n"
        f"                           {yellow('APEX STATS TRACKER')}\n"
        f"{equals}\n"
        f" {purple('[ ACCOUNT ]')} {cmd('account')} {k} {w} {orange('[lvl]')} {note('(Sets/Syncs totals)')}"
        f" | {cmd('accountl')} {lvl} {note('(Level)')}\n"
        f" {blue('[ BASE ]')}    {cmd('base')} <name> {k} {w} {note('(Sets/Syncs legend totals)')}\n"
        f" {cyan('[ MATCH ]')}   {k} {w} <legend>"
        f" | {red('<n>k')} {note('(e.g. ')}{red('5k')}{note(' wraith)')}"
        f" | {green('<n>w')} | {orange('<n>l')} {note('(Add levels)')}\n"
        f" {note('[ STICKY ]')}  {cmd('p')} <name> {note('(Lock)')}"
        f" | {red('7')} {note('(')}{red('7k')}{note(', ')}{green('0w')}{note(')')}"
        f" | {red('7')} {green('1')} {note('(')}{red('7k')}{note(', ')}{green('1w')}{note(')')}"
        f" | {cmd('-')} {note('(Unlock)')}\n"
        f" {note('[ TABLES ]')}  {cmd('l')} {note('(Kills)')} | {cmd('lw')} {note('(Wins)')}"
        f" | {cmd('la')} {note('(A-Z)')} | {cmd('lm')} {note('(Recent)')} |\n"
        f"             {cmd('ls')} <name> {note('(Search)')} | {cmd('g')} {note('(Top Games)')}"
        f" | {cmd('k')} | {cmd('w')} {note('(By Period)')}\n"
        f" {note('[ SYSTEM ]')}  {cmd('report')} | {cmd('undo')} | {cmd('date')} YYYY-MM-DD | {cmd('date today')}"
        f" | {cmd('help')}\n"
        f"{dashes}\n"
        f" {note('Press Enter on an empty line to quit.')}\n"
    )


def help_text():
    """The 'help' screen: what each command does, with the main menu's colors."""
    k, w, lvl, c = red("<k>"), green("<w>"), orange("<lvl>"), steel
    sections = (
        (purple("[ ACCOUNT ]"), (
            (f"{c('account')} {k} {w} {orange('[lvl]')}", "1st: save totals. Later: log the gain"),
            (c("account"), "Show totals and current level"),
            (f"{c('accountl')} {lvl}", "Set the exact account level"))),
        (blue("[ BASE ]"), (
            (f"{c('base')} <name> {k} {w}", "1st: set legend totals. Later: log gain"),
            (c("base"), "List the legends with a base"),
            (f"{c('base')} <name> {red('0')} {green('0')}", "Remove a legend's base"))),
        (cyan("[ MATCH ]"), (
            (k, "Kills, 0 wins (e.g. 7)"),
            (f"{k} {w} [legend]", "Kills and wins (e.g. 7 1 wraith)"),
            (f"{k} <legend>", "Kills and 1 win (e.g. 5 wraith)"),
            (f"{red('<n>k')} [legend]", "Add n kills only"),
            (f"{green('<n>w')} [legend]", "Add n wins only"),
            (orange("<n>l"), "Add n account levels"))),
        (gray("[ STICKY ]"), (
            (f"{c('p')} <name>", "Lock a base legend for later entries"),
            (c("-"), "Unlock the legend"))),
        (gray("[ TABLES ]"), (
            (c("l"), "Legends by kills + top 3 this month"),
            (c("lw"), "Same, by wins"),
            (c("la"), "Same, A-Z"),
            (c("lm"), "Same, most recent match first"),
            (f"{c('ls')} <name>", "Same, only legends matching the name"),
            (f"{c('k')} | {c('w')}", "Kills | wins per legend, by period"),
            (c("g"), "Top 10 games this month + monthly bests"),
            (c("log"), "Recent matches and recent levels"))),
        (gray("[ SYSTEM ]"), (
            (c("report"), "Totals, summaries and levels gained"),
            (c("undo"), "Revert the last action (repeatable)"),
            (f"{c('date')} YYYY-MM-DD", "Use this date for the next entries"),
            (c("date today"), "Back to today's date"),
            (c("help"), "This screen"))),
    )
    equals = "=" * 79
    out = ["", equals, f"                       {yellow('APEX STATS TRACKER - HELP')}", equals]
    for tag, rows in sections:
        for i, (cell, what) in enumerate(rows):
            left = tag + " " * (11 - visible_len(tag)) if i == 0 else " " * 11
            out.append(f" {left} {cell}{' ' * (HELP_CMD_W - visible_len(cell))} {gray(what)}")
    out += ["-" * 79,
            " " + gray("Lowering an account, base or level value asks y/n first."),
            " " + gray("Legend names can be shortened (wra = Wraith); a new name asks y/n first.")]
    return "\n".join(out) + "\n"
