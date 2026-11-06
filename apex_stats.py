#!/usr/bin/env python3
"""Apex Legends - registro statistiche su .txt (solo libreria standard).

Uso:
  python apex_stats.py add <kills> <wins> [--l NAME] [--date "YYYY-MM-DD HH:MM"]
  python apex_stats.py report
  python apex_stats.py l
  python apex_stats.py m
  python apex_stats.py          (modalita' interattiva: "<kills> <wins> <legend>", m/report/l, q/invio vuoto = esci)
  Opzione globale: --dir <cartella>  (default: ./apex_data accanto allo script)

Rotazione per mese di calendario: un file per mese (apex_stats_YYYY-MM.txt).

Formato file (parsing O(1) per riga tramite prefisso costante nella 1a colonna):
  @FILE  mese del file       @HIST  totali storici dei mesi precedenti
  @PREV  totali per mese (ultimi 11 mesi di calendario, per semestrale/annuale)
  @HL    totali storici per leggenda (mesi precedenti)
  @PL    totali per mese e leggenda (ultimi 11 mesi)
  L      singolo log         (resoconti dopo "# RESOCONTI": ricalcolati, non letti)
  #      intestazioni/commenti (ignorate dal parser)
"""
import argparse
import os
import re
import sys
from datetime import datetime

SEMI_MONTHS = 6
YEAR_MONTHS = 12
FNAME = "apex_stats_{}.txt"
FRE = re.compile(r"^apex_stats_(\d{4}-\d{2})\.txt$")
FOOTER_MARK = "# RESOCONTI"
NO_LEGEND = "-"
DFMT = "%Y-%m-%d %H:%M"

# Aggregati: LOG, KILL, VITTORIE
AGG = (("LOG", 6), ("KILL", 8), ("VITTORIE", 8))
DER = (("KILL/LOG", 8), ("WIN/LOG", 7))
NA = len(AGG)
TAG_W, REF_W, LEG_W = 7, 12, 12


def zero():
    return [0] * NA


def vadd(a, b):
    return [x + y for x, y in zip(a, b)]


def ints(cells):
    return [int(x) for x in cells[:NA]]


def midx(month):
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def log_agg(logs):
    t = zero()
    for _, _, k, w in logs:
        t[0] += 1; t[1] += k; t[2] += w
    return t


def legend_agg(logs):
    d = {}
    for _, leg, k, w in logs:
        t = d.setdefault(leg, zero())
        t[0] += 1; t[1] += k; t[2] += w
    return d


def periods(month, cur, hist, prev):
    """(mensile, semestrale, annuale, storico); prev = [(mese, valori)]."""
    ci = midx(month)
    semi = year = cur
    for m, v in prev:
        d = ci - midx(m)
        if d < SEMI_MONTHS:
            semi = vadd(semi, v)
        if d < YEAR_MONTHS:
            year = vadd(year, v)
    return cur, semi, year, vadd(hist, cur)


def vals_cells(vals, cols=AGG):
    return " | ".join(f"{v:>{w}}" for v, (_, w) in zip(vals, cols))


def row(tag, ref, vals):
    return f"{tag:<{TAG_W}} | {ref:<{REF_W}} | " + vals_cells(vals)


def derived(t):
    n = t[0]
    if not n:
        return ["-"] * len(DER)
    return [f"{t[1] / n:.2f}", f"{t[2] / n:.2f}"]


def with_der(t):
    return vals_cells(t) + " | " + vals_cells(derived(t), DER)


def sum_row(label, t):
    return f"{label:<{REF_W}} | " + with_der(t)


def pl_row(m, leg, t):
    return f"{'@PL':<{TAG_W}} | {m:<7} | {leg:<{LEG_W}} | " + vals_cells(t)


def log_row(r):
    d, leg, k, w = r
    return f"{'L':<{TAG_W}} | {d:<16} | {leg:<{LEG_W}} | {k:>4} | {w:>8}"


AGG_NAMES = [n for n, _ in AGG]
DER_NAMES = [n for n, _ in DER]
LOG_HEAD = f"{'# LOG':<{TAG_W}} | {'DATA':<16} | {'LEGGENDA':<{LEG_W}} | {'KILL':>4} | {'VITTORIE':>8}"
AGG_HEAD = row("# TIPO", "RIFERIMENTO", AGG_NAMES)
HL_HEAD = row("# TIPO", "LEGGENDA", AGG_NAMES)
PL_HEAD = f"{'# TIPO':<{TAG_W}} | {'MESE':<7} | {'LEGGENDA':<{LEG_W}} | " + vals_cells(AGG_NAMES)
SUM_HEAD = f"{'RIFERIMENTO':<{REF_W}} | " + vals_cells(AGG_NAMES) + " | " + vals_cells(DER_NAMES, DER)
W = max(len(SUM_HEAD), len(AGG_HEAD), len(PL_HEAD), len(LOG_HEAD))
LREP_HEAD = f"{'# LEGGENDA':<{LEG_W}} | {'PERIODO':<{REF_W}} | " + vals_cells(AGG_NAMES) + " | " + vals_cells(DER_NAMES, DER)
PERIOD_LABELS = ("MESE {}", "SEMESTRALE", "ANNUALE", "STORICO")


def render(month, hist, prev, logs, hl, pl):
    eq, dash = "=" * W, "-" * W
    out = [
        eq,
        "  APEX LEGENDS - REGISTRO STATISTICHE",
        f"  MESE {month}      LOG {len(logs)}",
        eq,
        f"{'@FILE':<{TAG_W}} | {month}",
        "# @HIST = totali storici dei mesi precedenti",
        "# @PREV = totali per mese (ultimi 11 mesi)",
        AGG_HEAD,
        dash,
        row("@HIST", f"< {month}", hist),
    ]
    out += [row("@PREV", m, t) for m, t in prev]
    out += ["", "# @HL = totali storici per leggenda (mesi precedenti)", HL_HEAD, dash]
    out += [row("@HL", leg, hl[leg]) for leg in sorted(hl)]
    out += ["", "# @PL = totali per mese e leggenda (ultimi 11 mesi)", PL_HEAD, dash]
    out += [pl_row(m, leg, t) for m, leg, t in pl]
    out += ["", eq, LOG_HEAD, dash]
    out += [log_row(r) for r in logs]
    out += ["", eq, summary(month, hist, prev, logs)]
    return "\n".join(out)


def summary(month, hist, prev, logs):
    out = [f"{FOOTER_MARK}  (aggiornati: {datetime.now():{DFMT}})", SUM_HEAD, "-" * W]
    for lbl, t in zip(PERIOD_LABELS, periods(month, log_agg(logs), hist, prev)):
        out.append(sum_row(lbl.format(month), t))
    out.append("=" * W)
    return "\n".join(out) + "\n"


def load(path):
    hist, prev, logs, hl, pl = zero(), [], [], {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            c = line.split("|")
            k = c[0].strip()
            if k == "L":
                logs.append((c[1].strip(), c[2].strip(), int(c[3]), int(c[4])))
            elif k == "@HIST":
                hist = ints(c[2:])
            elif k == "@PREV":
                prev.append((c[1].strip(), ints(c[2:])))
            elif k == "@HL":
                hl[c[1].strip()] = ints(c[2:])
            elif k == "@PL":
                pl.append((c[1].strip(), c[2].strip(), ints(c[3:])))
            elif k == FOOTER_MARK:
                break  # footer ricalcolato: inutile leggerlo
    return hist, prev, logs, hl, pl


def current_month(d):
    best = ""
    if os.path.isdir(d):
        for name in os.listdir(d):
            m = FRE.match(name)
            if m and m.group(1) > best:
                best = m.group(1)
    return best


def current_path(d):
    cur = current_month(d)
    if not cur:
        raise ValueError("Nessun dato registrato.")
    return cur, os.path.join(d, FNAME.format(cur))


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def clean(s, w):
    s = (s or "").replace("|", "/").strip().capitalize()[:w]
    return s or NO_LEGEND


def footer(text):
    i = text.find(FOOTER_MARK)
    return text[i:] if i >= 0 else ""


def save_log(d, kills, wins, legend=None, date=None):
    """Salva un log (1 lettura + 1 scrittura atomica). Errori -> ValueError."""
    if kills < 0 or wins < 0:
        raise ValueError("Errore: kills e wins non possono essere negativi.")
    try:
        dt = datetime.strptime(date, DFMT) if date else datetime.now()
    except ValueError:
        raise ValueError("Errore: data nel formato 'YYYY-MM-DD HH:MM'.") from None
    date, month = dt.strftime(DFMT), dt.strftime("%Y-%m")
    rec = (date, clean(legend, LEG_W), kills, wins)

    os.makedirs(d, exist_ok=True)
    cur = current_month(d)
    if month < cur:
        raise ValueError(f"Errore: il mese {month} e' gia' chiuso (file corrente: {cur}).")
    if cur:
        hist, prev, logs, hl, pl = load(os.path.join(d, FNAME.format(cur)))
    else:
        hist, prev, logs, hl, pl = zero(), [], [], {}, []

    if cur and month > cur:  # nuovo mese -> nuovo file, totali portati in header
        ni = midx(month)
        keep = lambda m: ni - midx(m) < YEAR_MONTHS
        hist = vadd(hist, log_agg(logs))
        prev = [(m, v) for m, v in prev + [(cur, log_agg(logs))] if keep(m)]
        la = legend_agg(logs)
        for leg, t in la.items():
            hl[leg] = vadd(hl.get(leg, zero()), t)
        pl = [x for x in pl + [(cur, leg, la[leg]) for leg in sorted(la)] if keep(x[0])]
        logs = []

    logs.append(rec)
    logs.sort(key=lambda r: r[0])
    path = os.path.join(d, FNAME.format(month))
    text = render(month, hist, prev, logs, hl, pl)
    write_atomic(path, text)
    return path, text, len(logs), rec


def cmd_add(a):
    try:
        path, text, n, _ = save_log(a.dir, a.kills, a.wins, a.legend, a.date)
    except ValueError as e:
        sys.exit(str(e))
    print(f"Salvato in {path} ({n} log nel mese)\n")
    print(footer(text), end="")


def interactive(d):
    print('Modalita\' rapida: "<kills> <wins> <legend>"  (es. 5 1 wraith)')
    print("Comandi: m | report | l   -   q o invio vuoto = esci")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd = line.lower()
        if not cmd or cmd == "q":
            break
        parts = line.split()
        try:
            if cmd in VIEWS:
                print(VIEWS[cmd](d), end="")
                continue
            if len(parts) < 2:
                raise ValueError('Formato: <kills> <wins> <legend>  (es. 5 1 wraith)')
            try:
                kills, wins = int(parts[0]), int(parts[1])
            except ValueError:
                raise ValueError("Errore: kills e wins devono essere numeri interi.") from None
            _, _, n, rec = save_log(d, kills, wins, " ".join(parts[2:]))
        except ValueError as e:
            print(e)
            continue
        print(f"  OK  {rec[1]}  KILL {rec[2]}  VITTORIE {rec[3]}  ({rec[0][:7]}: {n} log)")


def legend_report(month, logs, hl, pl):
    la = legend_agg(logs)
    by_leg = {}
    for m, leg, t in pl:
        by_leg.setdefault(leg, []).append((m, t))
    dash = "-" * len(LREP_HEAD)
    out = [f"# RESOCONTI PER LEGGENDA  (mese corrente: {month})", LREP_HEAD, dash]
    for leg in sorted(set(hl) | set(by_leg) | set(la)):
        ps = periods(month, la.get(leg, zero()), hl.get(leg, zero()), by_leg.get(leg, []))
        for i, (lbl, t) in enumerate(zip(PERIOD_LABELS, ps)):
            out.append(f"{leg if i == 0 else '':<{LEG_W}} | {lbl.format(month):<{REF_W}} | " + with_der(t))
        out.append(dash)
    return "\n".join(out) + "\n"


def report_text(d):
    cur, path = current_path(d)
    hist, prev, logs, _, _ = load(path)
    return f"File: {path}\n\n" + summary(cur, hist, prev, logs)


def legend_text(d):
    cur, path = current_path(d)
    _, _, logs, hl, pl = load(path)
    return f"File: {path}\n\n" + legend_report(cur, logs, hl, pl)


def m_text(d):
    cur, path = current_path(d)
    t = log_agg(load(path)[2])
    return f"MESE {cur}  |  KILL {t[1]}  |  VITTORIE {t[2]}\n"


VIEWS = {"report": report_text, "l": legend_text, "m": m_text}


def cmd_view(a):
    try:
        print(VIEWS[a.cmd](a.dir), end="")
    except ValueError as e:
        sys.exit(str(e))


USAGE_ADD = 'python apex_stats.py add <kills> <wins> [--l NAME] [--date "YYYY-MM-DD HH:MM"]   # legend defaults to "-"'
USAGE_REPORT = "python apex_stats.py report   # time-based summaries of the current file"
USAGE_L = "python apex_stats.py l   # summaries grouped by legend"
USAGE_M = "python apex_stats.py m   # total kills and wins of the current file"
USAGE_DIR = "python apex_stats.py --dir <path> ...   # data folder; default is ./apex_data next to the script"
USAGE_REPL = "python apex_stats.py   # interactive mode: '<kills> <wins> <legend>' per line, m/report/l, q or blank to quit"
USAGE = "\n  " + "\n  ".join((USAGE_ADD, USAGE_REPORT, USAGE_L, USAGE_M, USAGE_DIR, USAGE_REPL))
DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apex_data")


def main():
    if len(sys.argv) == 1:
        interactive(DEFAULT_DIR)
        return
    ap = argparse.ArgumentParser(usage=USAGE, description="Statistiche Apex Legends su .txt")
    ap.add_argument("--dir", metavar="<path>", default=DEFAULT_DIR,
                    help="cartella dati (default: ./apex_data accanto allo script)")
    sp = ap.add_subparsers(dest="cmd", required=True, metavar="{add,report,l,m}")
    p = sp.add_parser("add", prog="apex_stats.py add", usage="\n  " + USAGE_ADD,
                      help="registra un log (kill e vittorie)")
    p.add_argument("kills", type=int, metavar="<kills>", help="kill della sessione")
    p.add_argument("wins", type=int, metavar="<wins>", help="vittorie della sessione")
    p.add_argument("--l", dest="legend", metavar="NAME", help='leggenda (default: "-")')
    p.add_argument("--date", metavar='"YYYY-MM-DD HH:MM"', help="data del log (default: adesso)")
    p.set_defaults(fn=cmd_add)
    for name, usage, hlp in (("report", USAGE_REPORT, "resoconti del mese corrente"),
                             ("l", USAGE_L, "resoconti per leggenda"),
                             ("m", USAGE_M, "kill e vittorie totali del file corrente")):
        sp.add_parser(name, prog=f"apex_stats.py {name}", usage="\n  " + usage,
                      help=hlp).set_defaults(fn=cmd_view)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
