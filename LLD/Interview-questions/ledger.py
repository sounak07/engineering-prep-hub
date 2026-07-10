"""
Thread-safe transaction ledger — Python port of the Java design.

Primitive mapping (Java -> Python):
    ReentrantLock            -> threading.Lock
    ConcurrentHashMap        -> dict guarded by a lock (see note below)
    ConcurrentLinkedQueue    -> collections.deque (append/popleft are O(1))
    ConcurrentSkipListMap    -> sortedcontainers.SortedDict guarded by a lock
                                 (stdlib has no concurrent sorted map; see
                                 the docstring at the bottom for a pure-stdlib
                                 fallback using bisect)
    AtomicLong                -> itertools.count() + a small lock, or just
                                 an int protected by a lock

Note on "guarded by a lock": CPython's GIL makes a *single* dict/list
operation atomic, but every operation here is a *compound* check-then-act
(e.g. "read balance, decide if sufficient, write new balance"), and the GIL
gives you NO atomicity across multiple bytecodes. So locks are required
here for the same reason they were in Java — the GIL is not a substitute
for correctness, only an implementation detail of the interpreter.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from itertools import count
from typing import Optional

from sortedcontainers import SortedDict


class TransactionType(Enum):
    DEPOSIT = auto()
    WITHDRAW = auto()
    TRANSFER = auto()


@dataclass(frozen=True)
class Transaction:
    id: int
    type: TransactionType
    from_account_id: Optional[str]
    to_account_id: Optional[str]
    amount_cents: int
    timestamp_ms: int


class InsufficientFundsError(Exception):
    def __init__(self, account_id: str, balance: int, requested: int):
        super().__init__(
            f"Account {account_id} has {balance} but requested {requested}"
        )


class _Account:
    """Internal — never exposed outside the ledger."""

    __slots__ = ("id", "balance_cents", "lock", "transactions")

    def __init__(self, account_id: str, initial_balance_cents: int):
        self.id = account_id
        self.balance_cents = initial_balance_cents
        self.lock = threading.Lock()
        self.transactions: deque[Transaction] = deque()


class TransactionLedger:
    def __init__(self):
        self._accounts: dict[str, _Account] = {}
        self._accounts_lock = threading.Lock()  # guards inserts into _accounts
        self._by_timestamp: SortedDict[int, deque[Transaction]] = SortedDict()
        self._by_timestamp_lock = threading.Lock()
        self._id_counter = count(1)
        self._id_lock = threading.Lock()

    # ---------- account management ----------

    def create_account(self, account_id: str, initial_balance_cents: int = 0) -> None:
        with self._accounts_lock:
            self._accounts.setdefault(
                account_id, _Account(account_id, initial_balance_cents)
            )

    def get_balance(self, account_id: str) -> int:
        acc = self._get_account_or_raise(account_id)
        with acc.lock:
            return acc.balance_cents

    def _get_account_or_raise(self, account_id: str) -> _Account:
        acc = self._accounts.get(account_id)
        if acc is None:
            raise KeyError(f"Unknown account: {account_id}")
        return acc

    # ---------- core operations ----------

    def deposit(self, account_id: str, amount_cents: int) -> Transaction:
        self._require(amount_cents > 0, "amount must be positive")
        acc = self._get_account_or_raise(account_id)
        with acc.lock:
            acc.balance_cents += amount_cents
            return self._record(TransactionType.DEPOSIT, None, account_id,
                                 amount_cents, [acc])

    def withdraw(self, account_id: str, amount_cents: int) -> Transaction:
        self._require(amount_cents > 0, "amount must be positive")
        acc = self._get_account_or_raise(account_id)
        with acc.lock:
            if acc.balance_cents < amount_cents:
                raise InsufficientFundsError(account_id, acc.balance_cents, amount_cents)
            acc.balance_cents -= amount_cents
            return self._record(TransactionType.WITHDRAW, account_id, None,
                                 amount_cents, [acc])

    def transfer(self, from_id: str, to_id: str, amount_cents: int) -> Transaction:
        self._require(amount_cents > 0, "amount must be positive")
        if from_id == to_id:
            raise ValueError("Cannot transfer to the same account")

        from_acc = self._get_account_or_raise(from_id)
        to_acc = self._get_account_or_raise(to_id)

        # Deadlock avoidance: acquire locks in a fixed global order (by id),
        # regardless of which side is "from" and which is "to".
        first, second = sorted((from_acc, to_acc), key=lambda a: a.id)

        with first.lock:
            with second.lock:
                if from_acc.balance_cents < amount_cents:
                    raise InsufficientFundsError(from_id, from_acc.balance_cents, amount_cents)
                from_acc.balance_cents -= amount_cents
                to_acc.balance_cents += amount_cents
                return self._record(TransactionType.TRANSFER, from_id, to_id,
                                     amount_cents, [from_acc, to_acc])

    # ---------- query operations ----------

    def get_transactions(self, account_id: str) -> list[Transaction]:
        """O(k), k = number of transactions touching this account."""
        acc = self._get_account_or_raise(account_id)
        return list(acc.transactions)

    def get_transactions_by_timestamp_range(
        self, start_ms_inclusive: int, end_ms_inclusive: int
    ) -> list[Transaction]:
        """O(log n + m): n = distinct timestamps, m = matches in range."""
        result: list[Transaction] = []
        with self._by_timestamp_lock:
            keys = self._by_timestamp.irange(start_ms_inclusive, end_ms_inclusive)
            for k in keys:
                result.extend(self._by_timestamp[k])
        return result

    # ---------- internal helpers ----------

    def _record(self, type_: TransactionType, from_id: Optional[str],
                to_id: Optional[str], amount_cents: int,
                involved: list[_Account]) -> Transaction:
        with self._id_lock:
            txn_id = next(self._id_counter)
        ts = int(time.time() * 1000)
        txn = Transaction(txn_id, type_, from_id, to_id, amount_cents, ts)

        for acc in involved:
            acc.transactions.append(txn)

        with self._by_timestamp_lock:
            self._by_timestamp.setdefault(ts, deque()).append(txn)

        return txn

    @staticmethod
    def _require(cond: bool, msg: str) -> None:
        if not cond:
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Pure-stdlib fallback for _by_timestamp, if you can't add sortedcontainers:
#
#   import bisect
#   self._timestamps: list[int] = []          # kept sorted
#   self._by_timestamp: dict[int, deque] = {}
#
#   # insert:
#   if ts not in self._by_timestamp:
#       bisect.insort(self._timestamps, ts)    # O(n) — list shift, not O(log n)
#       self._by_timestamp[ts] = deque()
#   self._by_timestamp[ts].append(txn)
#
#   # range query:
#   lo = bisect.bisect_left(self._timestamps, start_ms_inclusive)
#   hi = bisect.bisect_right(self._timestamps, end_ms_inclusive)
#   for ts in self._timestamps[lo:hi]:
#       result.extend(self._by_timestamp[ts])
#
# Note the honest tradeoff: bisect.bisect is O(log n) to *find* the slice,
# but bisect.insort is O(n) to *insert* because inserting into a Python list
# shifts every element after it. SortedDict from sortedcontainers uses a
# load-balanced list-of-lists internally to get O(sqrt(n)) amortized insert
# in practice (better than a plain list, though not a true O(log n) skip
# list). Whether that matters depends entirely on write volume — for a
# ledger with a few thousand transactions/sec, sortedcontainers is fine;
# for a much higher-throughput system you'd reach for an actual balanced
# tree or push this into a database index instead of an in-process structure.
# ---------------------------------------------------------------------------