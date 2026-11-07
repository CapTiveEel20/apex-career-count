"""The only way to write a file: write to `.tmp`, then swap it in with os.replace."""
import os


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
