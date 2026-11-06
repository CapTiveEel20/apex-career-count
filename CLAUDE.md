# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

User-facing documentation lives in `README.md`. This file holds only the constraints for AI agents working on the code.

## STRICT CHAT RULE (from the user, applies to every interaction)

Whenever you use file-writing tools (Write, Edit, etc.), your chat reply must be exactly the single word `DONE`. Output nothing else: no summaries, diffs, explanations, or acknowledgement of this rule.

## System constraints

- **No external libraries.** Use only the Python standard library.
- **Keep I/O low.**
  - Every operation reads only the current (newest) monthly file, once. Never reopen older files.
  - Historical, six-month and yearly figures come from the totals carried forward in the current file's header (`@HIST`, `@PREV`, `@HL`, `@PL`).
  - Parsing stays O(1) per line: `load` dispatches on the constant prefix in the first `|`-separated column and stops at the `# RESOCONTI` footer.
- **Write atomically.** Every save goes through `write_atomic` (write to `.tmp`, then `os.replace`), and each operation writes at most one file.
