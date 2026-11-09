"""Shared test base: a Session on a temporary data folder, so no test touches apex_data/."""
import contextlib
import io
import os
import tempfile
import unittest

from apex.storage.account_file import account_path, load_acct
from apex.storage.monthly_file import load, month_path
from apex.ui.repl import Session


class SessionCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.d = tmp.name
        self.answer = True  # what confirm() replies
        self.asked = 0  # how many times confirm() was called
        self.create_legends = True  # what confirm_legend() replies
        self.new_legends = []  # the names confirm_legend() was asked about
        self.session = Session(self.d, confirm=self._confirm, confirm_legend=self._confirm_legend)

    def _confirm(self):
        self.asked += 1
        return self.answer

    def _confirm_legend(self, name):
        self.new_legends.append(name)
        return self.create_legends

    def do(self, *lines):
        """Run each line; returns the text printed by the last one."""
        out = ""
        for line in lines:
            out = self.session.handle(line)
        return out

    def do_quietly(self, *lines):
        """Like do, also returning what was warned on stderr: (text, warnings)."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = self.do(*lines)
        return out, err.getvalue()

    def month(self, name):
        return load(self.month_file(name))

    def month_file(self, name):
        return month_path(self.d, name)

    def has_month(self, name):
        return os.path.exists(self.month_file(name))

    def account(self):
        return load_acct(self.d).account

    def bases(self):
        return load_acct(self.d).bases

    def account_text(self):
        with open(account_path(self.d), encoding="utf-8") as f:
            return f.read()

    def write_account_text(self, text):
        with open(account_path(self.d), "w", encoding="utf-8") as f:
            f.write(text)

    def month_text(self, name):
        with open(self.month_file(name), encoding="utf-8") as f:
            return f.read()

    def write_month_text(self, name, text):
        with open(self.month_file(name), "w", encoding="utf-8") as f:
            f.write(text)
