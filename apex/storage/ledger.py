"""The Ledger: both data files (the monthly file and account_stats.txt) for the length of one command.

Each file is read at most once, changes stay in memory, and leaving the `with` block commits them
together (nothing is written if the block raises). Commands never touch the files directly.
"""
import os
from datetime import datetime

from apex.config import ACC_TAG, ACCOUNT_FILE, DFMT, SRC_ACCOUNT
from apex.core.levels import latest_level
from apex.core.parsing import parse_when
from apex.core.records import Change, Month, Stored
from apex.storage.account_file import account_path, load_acct, render_acct
from apex.storage.atomic import FileChange, commit_files
from apex.storage.monthly_file import carried_elsewhere, current_month, month_path, read_month, render, roll_over


def _now():
    return f"{datetime.now():{DFMT}}"


class Ledger:
    """Use as `with Ledger(d, when) as ledger:`. when = the command's date (None = now), parsed on first use."""

    def __init__(self, d, when=None):
        self.d, self._when, self._dt = d, when, None
        self._month, self._m, self._text = "", None, None  # month name, its Month, its text on disk
        self._account, self._bases, self._damaged, self._acct_read = None, None, [], False
        self._month_dirty = self._acct_dirty = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type is None:
            self._commit()

    @property
    def _date(self):
        if self._dt is None:
            self._dt = parse_when(self._when)
        return self._dt

    @property
    def stamp(self):
        """The command's date and time, the same for everything it records."""
        return self._date.strftime(DFMT)

    def _read_month(self):
        if self._m is not None:
            return
        self._month = current_month(self.d)
        if self._month:
            self._text, self._m = read_month(month_path(self.d, self._month))
        else:
            self._m = Month.empty()

    @property
    def month(self):
        """Name of the month held ('' if no file exists and nothing was opened)."""
        self._read_month()
        return self._month

    @property
    def current(self):
        """The Month held: the newest file, or the month opened by open_month."""
        self._read_month()
        return self._m

    def open_month(self, any_month=False):
        """The Month a record of this command goes into, rolled over in memory if it is a new month.
        An older month is closed: ValueError, unless any_month (undated records such as base changes
        go into the newest file)."""
        dt = self._date
        self._read_month()
        month = dt.strftime("%Y-%m")
        if month < self._month:
            if not any_month:
                raise ValueError(f"Error: month {month} is already closed (current file: {self._month}).")
            return self._m
        if self._month and month > self._month:
            if self._m.damaged:  # their totals would be left out of every later month
                name = os.path.basename(month_path(self.d, self._month))
                raise ValueError(f"Error: {name} has damaged lines (@BAD); fix or delete them by hand "
                                 f"before the first record of {month}. Nothing was saved.")
            self._m = roll_over(self._month, month, dt.date(), self._m)
            self._text = None  # a new file: nothing to put back if the commit fails
        self._month = month
        return self._m

    def _read_acct(self):
        if not self._acct_read:
            data = load_acct(self.d)
            if data.account_damaged:  # unknown totals must not be saved over, or treated as never set
                raise ValueError(f"Error: the {ACC_TAG} line of {ACCOUNT_FILE} is damaged; "
                                 "fix it by hand. Nothing was saved.")
            self._account, self._bases, self._damaged = data
            self._acct_read = True

    @property
    def account(self):
        """The Stored global account totals, or None if never set."""
        self._read_acct()
        return self._account

    @property
    def bases(self):
        """{legend: Stored}."""
        self._read_acct()
        return self._bases

    def level(self):
        """Current account level: the most recently recorded one; 0 if none."""
        return latest_level(self.current.logs, self.current.lv)

    def _set_account(self, value):
        self._read_acct()
        self._account = value
        self._acct_dirty = True
        return value

    def _set_base(self, legend, value):
        if value:
            self.bases[legend] = value
        else:
            self.bases.pop(legend, None)
        self._acct_dirty = True

    def add(self, entry):
        """Log an Entry of the month opened with open_month. If it counts for the account (acc = 1)
        the totals move with it; an account gain also keeps the totals before it, under the same ID."""
        m = self.current
        m.logs.append(entry)
        m.logs.sort(key=lambda e: (e.date, e.id))
        self._month_dirty = True
        if entry.acc:
            acc = self.account
            if entry.src == SRC_ACCOUNT:
                m.changes.append(Change(entry.id, entry.date, ACC_TAG, acc))
            self._set_account(Stored(acc.kills + entry.kills, acc.wins + entry.wins, _now()))

    def _add_change(self, target, old):
        m = self.open_month(any_month=True)
        m.changes.append(Change(m.next_id(), self.stamp, target, old))
        self._month_dirty = True

    def change_account(self, kills, wins):
        """Replace the account totals without logging a gain (first save, confirmed lowering), undoable.
        Returns the new totals."""
        self._add_change(ACC_TAG, self.account)
        return self._set_account(Stored(kills, wins, _now()))

    def change_base(self, legend, kills, wins):
        """Set or correct a legend's base without logging a gain, undoable. 0 0 is a valid base: the
        logged entries already cover its all-time totals."""
        self._add_change(legend, self.bases.get(legend))
        self._set_base(legend, Stored(kills, wins, _now()))

    def remove_base(self, legend):
        """Remove a legend's base, undoable."""
        self._add_change(legend, self.bases.get(legend))
        self._set_base(legend, None)

    def revert_last(self):
        """Take out the most recent action, every record with the highest ID, and put back what it
        changed: a Change restores the value it replaced; an Entry takes its kills/wins back out of the
        account totals, unless a Change already restored them. Returns (Entry or None, Change or None)."""
        m = self.current
        if not self._month:
            raise ValueError("No data recorded yet.")
        entry, change = m.last_action()
        if not (entry or change):
            raise ValueError("Nothing to undo.")
        if entry:
            m.logs.remove(entry)
        if change:
            m.changes.remove(change)
        self._month_dirty = True
        if change and change.is_account:
            self._set_account(change.old)
        elif change:
            self._set_base(change.target, change.old)
        if entry and entry.acc and not (change and change.is_account) and self.account:
            acc = self.account
            self._set_account(Stored(max(0, acc.kills - entry.kills), max(0, acc.wins - entry.wins), _now()))
        return entry, change

    def _commit(self):
        """Write what changed, the monthly file first, all or nothing. A month left with no records is
        deleted, so the previous month (untouched at rollover) becomes current again; unless it holds
        totals of earlier months that no other file has any more: it then stays, with no records."""
        changes = []
        if self._month_dirty:
            m = self._m
            keep = m.has_records or not carried_elsewhere(self.d, self._month, m)
            text = render(self._month, m) if keep else None
            changes.append(FileChange(month_path(self.d, self._month), text, self._text))
        if self._acct_dirty:
            changes.append(FileChange(account_path(self.d), render_acct(self._account, self._bases, self._damaged), None))
        if not changes:
            return
        try:
            os.makedirs(self.d, exist_ok=True)
            commit_files(changes)
        except OSError as e:
            raise ValueError(f"Error: could not save the data files ({e}).") from e
