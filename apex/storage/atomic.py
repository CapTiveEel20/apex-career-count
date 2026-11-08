"""The only way to write the data files: write to `.tmp`, then swap it in with os.replace."""
import os
from typing import NamedTuple, Optional

TMP = ".tmp"


class FileChange(NamedTuple):
    """One file of a commit: new = its new text (None = delete it); old = the text to put back if a
    later file fails (None = there was no file). The last file is never put back: nothing follows it."""
    path: str
    new: Optional[str]
    old: Optional[str]


def _write_tmp(path, text):
    with open(path + TMP, "w", encoding="utf-8") as f:
        f.write(text)


def _put_back(c):
    if c.old is not None:
        _write_tmp(c.path, c.old)
        os.replace(c.path + TMP, c.path)
    elif os.path.exists(c.path):
        os.remove(c.path)


def commit_files(changes):
    """Apply the changes in order, or none of them. Every new text is on disk before the first file
    is swapped; if a swap fails, the files already changed are put back and the OSError is raised."""
    applied = []
    try:
        for c in changes:
            if c.new is not None:
                _write_tmp(c.path, c.new)
        for c in changes:
            if c.new is None:
                os.remove(c.path)
            else:
                os.replace(c.path + TMP, c.path)
            applied.append(c)
    except OSError:
        for c in changes:
            if os.path.exists(c.path + TMP):
                os.remove(c.path + TMP)
        for c in reversed(applied):
            _put_back(c)
        raise
