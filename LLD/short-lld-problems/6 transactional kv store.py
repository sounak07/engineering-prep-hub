"""
RIPPLING PRACTICE — In-Memory Key-Value Store with Transactions
===============================================================
Often discussed alongside Rippling interviews (cache / transactional store).

Part 1: set / get / delete
Part 2: begin / commit / rollback  (single transaction)
Part 3: nested transactions

Patterns:
  * Memento-like layers — each transaction holds only its delta, not a full copy
  * Facade — TransactionalKeyValueStore exposes the interview API
  * Sentinel — _DELETED marks keys removed inside a transaction layer

Semantics:
  * Reads search innermost layer → … → committed store (read-your-writes)
  * commit merges top layer into parent; outermost commit persists to base
  * rollback discards top layer only
  * delete inside a transaction hides the key until commit/rollback resolves it
"""

from typing import Any, Dict, List

_DELETED = object()


class TransactionLayer:
    def __init__(self, name: str = None):
        self.changes: Dict[str, Any] = {}
        # Add named savepoints: savepoint("before_risky_op"), 
        # and let me roll back to a specific savepoint, not just one level.
        self.name = name


class TransactionalKeyValueStore:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._transactions: List[TransactionLayer] = []

    def _current_layer(self):
        if self._transactions:
            return self._transactions[-1]
        return None

    def begin(self):
        self._transactions.append(TransactionLayer())

    def set(self, key: str, value: Any):
        layer = self._current_layer()

        if layer:
            layer.changes[key] = value
        else:
            self._store[key] = value

    def delete(self, key: str):
        layer = self._current_layer()

        if layer:
            layer.changes[key] = _DELETED
        else:
            self._store.pop(key, None)

    def get(self, key: str):
        for layer in reversed(self._transactions):
            if key in layer.changes:
                value = layer.changes[key]

                if value is _DELETED:
                    return None

                return value

        return self._store.get(key)

    def rollback(self):
        if not self._transactions:
            raise RuntimeError("No active transaction")

        self._transactions.pop()

    def commit(self):
        if not self._transactions:
            raise RuntimeError("No active transaction")

        layer = self._transactions.pop()

        if self._transactions:
            parent = self._current_layer()

            for key, value in layer.changes.items():
                parent.changes[key] = value

        else:
            for key, value in layer.changes.items():
                if value is _DELETED:
                    self._store.pop(key, None)
                else:
                    self._store[key] = value


# I'd extract a TransactionManager that owns the committed store and transaction stack, 
# while keeping TransactionLayer as a simple delta object. 
# I wouldn't push transaction logic into the layer itself because commit, 
# rollback, and reads span multiple layers and are better managed centrally."

def _demo():
    db = TransactionalKeyValueStore()

    print("===== Basic Operations =====")
    db.set("x", 10)
    db.set("y", 20)

    print(db.get("x"))          # 10
    print(db.get("y"))          # 20

    db.delete("y")
    print(db.get("y"))          # None

    print("\n===== Single Transaction =====")

    db.begin()

    db.set("x", 100)
    db.set("z", 30)

    print(db.get("x"))          # 100
    print(db.get("z"))          # 30

    db.rollback()

    print(db.get("x"))          # 10
    print(db.get("z"))          # None

    print("\n===== Commit Transaction =====")

    db.begin()

    db.set("x", 200)
    db.delete("y")

    print(db.get("x"))          # 200

    db.commit()

    print(db.get("x"))          # 200
    print(db.get("y"))          # None

    print("\n===== Nested Transactions =====")

    db.begin()
    db.set("x", 1)

    db.begin()
    db.set("x", 2)

    db.begin()
    db.set("x", 3)

    print(db.get("x"))          # 3

    db.rollback()

    print(db.get("x"))          # 2

    db.commit()

    print(db.get("x"))          # 2

    db.commit()

    print(db.get("x"))          # 2

    print("\n===== Delete Inside Transaction =====")

    db.begin()

    db.delete("x")

    print(db.get("x"))          # None

    db.rollback()

    print(db.get("x"))          # 2

    print("\n===== Commit Delete =====")

    db.begin()

    db.delete("x")

    print(db.get("x"))          # None

    db.commit()

    print(db.get("x"))          # None

if __name__ == "__main__":
    _demo()
    