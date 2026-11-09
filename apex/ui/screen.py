"""Centered terminal output for interactive(): each block of text is centered on the current width,
and everything shown so far is drawn again when the window changes width.

Only the terminal loop goes through here: Session.handle and the views still return plain text.
"""
import os
import sys
import threading
import time
from collections import deque
from typing import NamedTuple

from apex.config import UI_WIDTH
from apex.display.colors import active, visible_len

CLEAR = "\033[H\033[2J\033[3J"  # cursor home, clear the window and its scrollback
POLL_SECONDS = 0.2  # how often the width is checked
HISTORY = 500  # items kept for drawing again
STD_INPUT_HANDLE, KEY_EVENT, VK_ESCAPE = 0xFFFFFFF6, 1, 0x1B  # Windows console API
ESCAPE_SETTLE_SECONDS = 0.05


class _Typed(NamedTuple):
    """A prompt and what was typed at it: placed at the left edge of the UI column, not centered."""
    text: str


def _is_divider(line):
    """A page divider: all '=' or all '-', as wide as the UI column. A table's rule fits its columns instead."""
    return len(line) == UI_WIDTH and set(line) in ({"="}, {"-"})


def _is_title(lines, i):
    """The line between two page dividers."""
    return 0 < i < len(lines) - 1 and _is_divider(lines[i - 1]) and _is_divider(lines[i + 1])


def center_block(text, cols):
    """text with every line moved right by the same amount, so that its widest line is centered in
    cols columns and table columns stay aligned. A block wider than cols stays at the left. Page
    dividers are stretched or cut to cols, and a title is centered on its own. cols = 0: unchanged."""
    if not cols:
        return text
    lines = text.split("\n")
    pad = " " * max(0, (cols - max(map(visible_len, lines))) // 2)

    def place(i, line):
        if _is_divider(line):
            return line[0] * cols
        if _is_title(lines, i):
            title = line.strip()
            return " " * max(0, (cols - visible_len(title)) // 2) + title
        return pad + line if line else line

    return "\n".join(place(i, line) for i, line in enumerate(lines))


def _margin(cols):
    return " " * max(0, (cols - UI_WIDTH) // 2)


def _render(item, cols):
    if isinstance(item, _Typed):
        return _margin(cols) + item.text + "\n"
    return center_block(item, cols)


class Screen:
    """columns() = the current terminal width (0 = plain output, nothing centered). The watcher thread
    (start) calls poll; show and read share a lock with it, so a redraw never lands inside a write."""

    def __init__(self, columns, out, reader=lambda: input(), discard_typing=lambda: None):
        self._columns, self._out, self._reader = columns, out, reader
        self._discard_typing = discard_typing  # empties a half-typed line, which a redraw wipes from view
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._items = deque(maxlen=HISTORY)
        self._prompt = None  # the prompt waiting for input, drawn again by a redraw
        self._cols = columns()  # the width everything on screen is centered for
        self._seen = None  # a new width noticed by the last poll

    def _write(self, text):
        self._out.write(text)
        self._out.flush()

    def show(self, text):
        """Print a block of text, centered."""
        with self._lock:
            self._items.append(text)
            self._write(center_block(text, self._cols))

    def read(self, prompt):
        """input(prompt), with the prompt at the left edge of the UI column. Returns the line typed;
        EOFError and KeyboardInterrupt pass through. The lock is free while waiting for input."""
        with self._lock:
            self._prompt = prompt
            self._write(_margin(self._cols) + prompt)
        line = None
        try:
            line = self._reader()
            return line
        finally:
            with self._lock:
                self._prompt = None
                if line is not None:
                    self._items.append(_Typed(prompt + line))

    def poll(self):
        """Draw everything again once a new width has held still for one poll, so that dragging the
        window edge does not redraw at every step."""
        cols = self._columns()
        with self._lock:
            if cols == self._cols:
                self._seen = None
            elif cols == self._seen:
                self._seen = None
                self._redraw(cols)
            else:
                self._seen = cols

    def _redraw(self, cols):
        if self._prompt is not None:  # otherwise text no longer visible would still be part of the line
            self._discard_typing()
        self._cols = cols
        body = "".join(_render(item, cols) for item in self._items)
        self._write(CLEAR + body + ("" if self._prompt is None else _margin(cols) + self._prompt))

    def _watch(self):
        while not self._stop.wait(POLL_SECONDS):
            try:
                self.poll()
            except OSError:  # the console is gone: nothing left to draw on
                return

    def start(self):
        threading.Thread(target=self._watch, daemon=True).start()

    def stop(self):
        self._stop.set()


def _terminal_columns():
    return os.get_terminal_size(sys.stdout.fileno()).columns


def _press_escape():
    """Windows console: press Esc, which empties the line being typed, and give input() time to see it."""
    import ctypes
    from ctypes import wintypes

    class Key(ctypes.Structure):
        _fields_ = [("down", wintypes.BOOL), ("repeat", wintypes.WORD), ("vk", wintypes.WORD),
                    ("scan", wintypes.WORD), ("char", wintypes.WCHAR), ("state", wintypes.DWORD)]

    class Record(ctypes.Structure):
        _fields_ = [("type", wintypes.WORD), ("key", Key)]

    k32 = ctypes.WinDLL("kernel32")
    k32.GetStdHandle.restype = wintypes.HANDLE
    k32.GetStdHandle.argtypes = [wintypes.DWORD]
    k32.WriteConsoleInputW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Record), wintypes.DWORD,
                                       ctypes.POINTER(wintypes.DWORD)]
    stdin = k32.GetStdHandle(STD_INPUT_HANDLE)
    for down in (True, False):
        record = Record(KEY_EVENT, Key(down, 1, VK_ESCAPE, 0, "\x1b", 0))
        k32.WriteConsoleInputW(stdin, ctypes.byref(record), 1, ctypes.byref(wintypes.DWORD()))
    time.sleep(ESCAPE_SETTLE_SECONDS)


def terminal_screen():
    """The Screen of this run. Output that is not a terminal stays plain; drawing again needs ANSI
    codes, so without colors (NO_COLOR) text is centered when printed but does not follow a resize."""
    if not sys.stdout.isatty():
        return Screen(lambda: 0, sys.stdout)
    screen = Screen(_terminal_columns, sys.stdout, discard_typing=_press_escape if os.name == "nt" else lambda: None)
    if active():
        screen.start()
    return screen
