"""
RIPPLING ROUND 2 — Design an Excel Sheet
========================================
API:
  set(cell, value_or_expression)   # e.g. set("A1", 5) or set("A2", "=A1+5")
  print()                          # show every cell's evaluated value

Formulas start with '=' and may reference other cells:
  "=A1+5"     -> value of A1, plus 5
  "=A3"       -> value of A3
  "=A1+A2-3"  -> left-to-right + / -

Two ideas the interviewer is looking for:
  * LAZY EVALUATION: set() only STORES the raw input. Nothing is computed until
    you read a cell (get/print). So a formula always reflects the latest inputs.
  * RECURSION: a formula references cells, which may themselves be formulas, so
    evaluation recurses until it bottoms out at literal numbers.

Design (OOP):
  * Cell        -> dumb value holder (encapsulates the raw input).
  * ExcelSheet  -> owns Map<ref, Cell>, resolves references, evaluates lazily,
                   and guards against reference cycles (A1 -> A2 -> A1).

Kept intentionally small (as asked). Follow-ups noted at the bottom.
"""

from __future__ import annotations

import re

# A cell reference is one-or-more letters followed by one-or-more digits: A1, B12.
_CELL_REF = re.compile(r"^[A-Za-z]+[0-9]+$")


class Cell:
    """Holds the raw input for a cell. It does NOT evaluate itself."""

    def __init__(self, raw: object) -> None:
        self.raw = raw

    @property
    def is_formula(self) -> bool:
        return isinstance(self.raw, str) and self.raw.startswith("=")

    def __repr__(self) -> str:
        return f"Cell({self.raw!r})"


class ExcelSheet:
    def __init__(self) -> None:
        self._cells: dict[str, Cell] = {}

    # ---------- Part 1: store (lazy — no computation here) ----------
    def set(self, ref: str, value_or_expression: object) -> None:
        """Store a literal value or a formula string. O(1). Never evaluates."""
        self._cells[ref] = Cell(value_or_expression)

    # ---------- Part 2: read (evaluate on demand, recursively) ----------
    def get(self, ref: str) -> float:
        """Evaluate a cell now, resolving any formulas/references it points to."""
        return self._evaluate(ref, visiting=set())

    def print(self) -> None:
        """Print every cell's evaluated value (sorted for stable output)."""
        for ref in sorted(self._cells):
            print(f"{ref} = {self.get(ref)}")

    # ---------- evaluation core ----------
    def _evaluate(self, ref: str, visiting: set[str]) -> float:
        if ref not in self._cells:
            raise ValueError(f"unknown cell: {ref}")
        if ref in visiting:                      # Part 3: cycle guard
            raise ValueError(f"cycle detected involving {ref}")

        cell = self._cells[ref]
        if not cell.is_formula:
            return self._to_number(cell.raw)

        visiting.add(ref)                        # mark on the current path
        result = self._eval_formula(cell.raw[1:], visiting)  # drop the leading '='
        visiting.discard(ref)                    # backtrack so diamonds are allowed
        return result

    def _eval_formula(self, expr: str, visiting: set[str]) -> float:
        # split keeping the operators: "A1+5-2" -> ["A1", "+", "5", "-", "2"]
        tokens = re.split(r"([+\-])", expr)
        total = self._eval_operand(tokens[0], visiting)
        i = 1
        while i < len(tokens):
            op, operand = tokens[i].strip(), tokens[i + 1]
            value = self._eval_operand(operand, visiting)
            total = total + value if op == "+" else total - value
            i += 2
        return total

    def _eval_operand(self, token: str, visiting: set[str]) -> float:
        token = token.strip()
        if _CELL_REF.match(token):               # a reference -> recurse
            return self._evaluate(token, visiting)
        return self._to_number(token)            # a literal number

    @staticmethod
    def _to_number(raw: object) -> float:
        if isinstance(raw, (int, float)):
            return raw
        text = str(raw).strip()
        return int(text) if text.lstrip("-").isdigit() else float(text)


# ---------------------------------------------------------------------------
# FOLLOW-UPS to mention out loud (don't code unless asked):
#   * Precedence / *, /, parentheses -> shunting-yard or a small expression tree
#     (Composite pattern) instead of left-to-right +/-.
#   * Memoize evaluated values + invalidate dependents on set() (dependency graph)
#     if reads dominate writes — that's the caching optimization, skipped here.
#   * Treat an unset referenced cell as 0 (Excel behavior) instead of erroring.
# ---------------------------------------------------------------------------


def _demo():
    sheet = ExcelSheet()
    sheet.set("A1", 5)
    sheet.set("A2", "=A1+5")      # 10
    sheet.set("A3", "=A2")        # 10
    sheet.set("A4", "=A1+A2+A3")  # 25
    sheet.set("A5", "=A4-A1")     # 20

    assert sheet.get("A1") == 5
    assert sheet.get("A2") == 10
    assert sheet.get("A3") == 10
    assert sheet.get("A4") == 25
    assert sheet.get("A5") == 20

    # lazy: change an input, dependents reflect it on next read
    sheet.set("A1", 100)
    assert sheet.get("A2") == 105
    assert sheet.get("A4") == 100 + 105 + 105  # 310

    sheet.print()

    # cycle is rejected
    sheet.set("B1", "=B2")
    sheet.set("B2", "=B1")
    try:
        sheet.get("B1")
        raise AssertionError("expected cycle error")
    except ValueError as e:
        assert "cycle" in str(e)

    # unknown reference is rejected
    sheet.set("C1", "=Z9")
    try:
        sheet.get("C1")
        raise AssertionError("expected unknown-cell error")
    except ValueError as e:
        assert "unknown" in str(e)

    print("All assertions passed ✔")


if __name__ == "__main__":
    _demo()
