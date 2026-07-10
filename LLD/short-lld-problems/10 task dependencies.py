"""
RIPPLING PROBLEM — Task Dependencies / DAG
==========================================
You have a list of tasks; each task may or may not depend on other tasks
("Task A can only run after B and C are done").

Part 1 (warm-up): model the tasks and print them in a readable format.
Part 2 (DAG follow-up): a task list with dependencies is a Directed Acyclic
Graph (edge dependency -> task). The usual follow-ups are:
    (a) produce a valid execution order        -> topological sort (Kahn's)
    (b) reject impossible task lists           -> cycle detection
    (c) which tasks can run in parallel        -> "levels" / batches

INTERVIEW TIP — clarify first:
  * Are dependencies given as "A depends on [B, C]" (deps) or
    "B unblocks [A]" (dependents)? Direction of the edge matters.
  * Can a dependency reference an unknown task? (we reject it)
  * Should ordering be deterministic? (we sort ties by name for stable output)

Modeling choice: edge B -> A means "B must finish before A".
  - indegree[A] = number of unfinished prerequisites of A.
  - dependents[B] = tasks waiting on B.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Task:
    name: str
    depends_on: list[str] = field(default_factory=list)


class TaskGraph:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._dependents: dict[str, list[str]] = {}  # prereq -> tasks waiting on it
        self._indegree: dict[str, int] = {}          # task  -> # of prerequisites

    # ---------- build ----------
    def add_task(self, name: str, depends_on: list[str] | None = None) -> None:
        """Register a task and its prerequisites. O(deps)."""
        depends_on = depends_on or []
        if name in self._tasks:
            raise ValueError(f"duplicate task: {name}")

        self._tasks[name] = Task(name, list(depends_on))
        self._indegree.setdefault(name, 0)
        self._dependents.setdefault(name, [])

        for prereq in depends_on:
            self._dependents.setdefault(prereq, []).append(name)
            self._indegree[name] += 1
            self._indegree.setdefault(prereq, 0)

    def _validate(self) -> None:
        """Every referenced prerequisite must be a known task."""
        for task in self._tasks.values():
            for prereq in task.depends_on:
                if prereq not in self._tasks:
                    raise ValueError(
                        f"task {task.name!r} depends on unknown task {prereq!r}"
                    )

    # ---------- Part 1: print ----------
    def print_tasks(self) -> None:
        """
        Print each task with its direct dependencies. O(V + E).
        Format (clarify with interviewer):
            Task-A depends on: B, C
            Task-D depends on: (none)
        """
        for name in sorted(self._tasks):
            deps = self._tasks[name].depends_on
            deps_str = ", ".join(sorted(deps)) if deps else "(none)"
            print(f"{name} depends on: {deps_str}")

    # ---------- Part 2a: valid execution order ----------
    def topological_order(self) -> list[str]:
        """
        A valid order to run all tasks (every prereq before its dependents).
        Kahn's algorithm (BFS on indegree). Ties broken by name for determinism.

        Time:  O(V + E)   Space: O(V)
        Raises ValueError if a cycle exists (no valid order).
        """
        self._validate()
        indegree = dict(self._indegree)
        # heap-like determinism via sorted seeding + sorted re-inserts
        ready = deque(sorted(n for n, d in indegree.items() if d == 0))
        order: list[str] = []

        while ready:
            node = ready.popleft()
            order.append(node)
            unlocked = []
            for dependent in self._dependents[node]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    unlocked.append(dependent)
            # keep output stable
            for n in sorted(unlocked):
                ready.append(n)

        if len(order) != len(self._tasks):
            stuck = [n for n in self._tasks if n not in set(order)]
            raise ValueError(f"cycle detected among tasks: {sorted(stuck)}")
        return order

    # ---------- Part 2b: cycle detection ----------
    def has_cycle(self) -> bool:
        """True if dependencies form a cycle (not a valid DAG). O(V + E)."""
        try:
            self.topological_order()
            return False
        except ValueError as e:
            # unknown-task errors aren't cycles; re-raise those
            if "cycle detected" in str(e):
                return True
            raise

    # ---------- Part 2c: parallel batches ----------
    def execution_batches(self) -> list[list[str]]:
        """
        Group tasks into levels that can run in parallel: every task in batch i
        has all prerequisites satisfied by batches < i. O(V + E).

        Returns [[names in wave 0], [wave 1], ...].
        """
        self._validate()
        indegree = dict(self._indegree)
        current = sorted(n for n, d in indegree.items() if d == 0)
        batches: list[list[str]] = []
        seen = 0

        while current:
            batches.append(current)
            seen += len(current)
            nxt: list[str] = []
            for node in current:
                for dependent in self._dependents[node]:
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        nxt.append(dependent)
            current = sorted(nxt)

        if seen != len(self._tasks):
            raise ValueError("cycle detected: cannot schedule all tasks")
        return batches


def _demo():
    g = TaskGraph()
    #   build -> test -> deploy
    #   build -> lint
    #   deploy needs both test and package; package needs build
    g.add_task("build")
    g.add_task("lint", ["build"])
    g.add_task("test", ["build"])
    g.add_task("package", ["build"])
    g.add_task("deploy", ["test", "package"])

    print("--- Part 1: tasks ---")
    g.print_tasks()

    print("\n--- Part 2a: execution order ---")
    order = g.topological_order()
    print(order)
    # build must come before everything; deploy last
    assert order.index("build") < order.index("test")
    assert order.index("build") < order.index("package")
    assert order.index("test") < order.index("deploy")
    assert order.index("package") < order.index("deploy")

    print("\n--- Part 2b: cycle detection ---")
    assert g.has_cycle() is False

    print("\n--- Part 2c: parallel batches ---")
    batches = g.execution_batches()
    print(batches)
    assert batches[0] == ["build"]
    assert batches[-1] == ["deploy"]
    assert sorted(batches[1]) == ["lint", "package", "test"]

    # a cyclic graph is rejected
    bad = TaskGraph()
    bad.add_task("a", ["b"])
    bad.add_task("b", ["a"])
    assert bad.has_cycle() is True
    try:
        bad.topological_order()
        raise AssertionError("expected cycle error")
    except ValueError as e:
        assert "cycle" in str(e)

    # unknown dependency is rejected
    ref = TaskGraph()
    ref.add_task("x", ["ghost"])
    try:
        ref.topological_order()
        raise AssertionError("expected unknown-task error")
    except ValueError as e:
        assert "unknown" in str(e)

    print("\nAll assertions passed ✔")


if __name__ == "__main__":
    _demo()
