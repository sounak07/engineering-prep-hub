from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


# =====================================================
# Models
# =====================================================

class ExpenseType(Enum):
    FOOD = "FOOD"
    ENTERTAINMENT = "ENTERTAINMENT"
    TRAVEL = "TRAVEL"
    HOTEL = "HOTEL"


class SellerType(Enum):
    RESTAURANT = "RESTAURANT"
    HOTEL = "HOTEL"
    AIRLINE = "AIRLINE"


@dataclass
class Expense:
    expense_id: str
    item_id: str
    expense_type: ExpenseType
    amount: Decimal  # money: base-10, exact sums; never float
    seller_type: SellerType
    seller_name: str
    trip_id: Optional[str] = None  # groups expenses for aggregate (trip-level) rules


@dataclass
class RuleViolation:
    expense_id: Optional[str]
    rule_name: str
    message: str


# =====================================================
# Validation Context
# =====================================================

class ValidationContext:

    def __init__(self) -> None:
        self.violations: list[RuleViolation] = []

    def add_violation(
        self,
        rule: "Rule",
        message: str,
        expense: Optional[Expense] = None,
    ) -> None:
        self.violations.append(
            RuleViolation(
                expense_id=expense.expense_id if expense else None,
                rule_name=rule.__class__.__name__,
                message=message,
            )
        )


# =====================================================
# Rule Interface
# =====================================================

class Rule(ABC):
    @abstractmethod
    def evaluate(self, expenses: list[Expense], context: ValidationContext) -> None:
        """
        Each rule receives ALL expenses and decides what to check:
          * per-expense rules iterate and flag individual expenses
          * trip-level rules aggregate across the whole list
        """
        ...


# =====================================================
# Expense Level Rules
# =====================================================

class MaxExpenseRule(Rule):

    def __init__(self, limit: Decimal) -> None:
        self.limit = Decimal(str(limit))

    def evaluate(
        self,
        expenses: list[Expense],
        context: ValidationContext,
    ) -> None:

        for expense in expenses:
            if expense.amount > self.limit:
                context.add_violation(
                    self,
                    f"Expense amount {expense.amount} exceeds limit {self.limit}",
                    expense,
                )


class RestaurantExpenseRule(Rule):

    def __init__(self, limit: Decimal) -> None:
        self.limit = Decimal(str(limit))

    def evaluate(
        self,
        expenses: list[Expense],
        context: ValidationContext,
    ) -> None:

        for expense in expenses:
            if (
                expense.seller_type == SellerType.RESTAURANT
                and expense.amount > self.limit
            ):
                context.add_violation(
                    self,
                    f"Restaurant expense exceeds limit {self.limit}",
                    expense,
                )


class EntertainmentNotAllowedRule(Rule):

    def evaluate(
        self,
        expenses: list[Expense],
        context: ValidationContext,
    ) -> None:

        for expense in expenses:
            if expense.expense_type == ExpenseType.ENTERTAINMENT:
                context.add_violation(
                    self,
                    "Entertainment expenses are not allowed",
                    expense,
                )


# =====================================================
# Trip Level Rules
# =====================================================

def group_by_trip(expenses: list[Expense]) -> dict[Optional[str], list[Expense]]:
    """Bucket expenses by trip_id so aggregate rules check each trip separately."""
    grouped: dict[Optional[str], list[Expense]] = {}
    for expense in expenses:
        grouped.setdefault(expense.trip_id, []).append(expense)
    return grouped


class TotalTripExpenseRule(Rule):

    def __init__(self, limit: Decimal) -> None:
        self.limit = Decimal(str(limit))

    def evaluate(
        self,
        expenses: list[Expense],
        context: ValidationContext,
    ) -> None:

        for trip_id, trip_expenses in group_by_trip(expenses).items():
            total = sum((expense.amount for expense in trip_expenses), Decimal(0))
            if total > self.limit:
                context.add_violation(
                    self,
                    f"Trip {trip_id} total ({total}) exceeds limit {self.limit}",
                )


class TotalFoodExpenseRule(Rule):

    def __init__(self, limit: Decimal) -> None:
        self.limit = Decimal(str(limit))

    def evaluate(
        self,
        expenses: list[Expense],
        context: ValidationContext,
    ) -> None:

        for trip_id, trip_expenses in group_by_trip(expenses).items():
            total_food = sum(
                (
                    expense.amount
                    for expense in trip_expenses
                    if expense.expense_type == ExpenseType.FOOD
                ),
                Decimal(0),
            )
            if total_food > self.limit:
                context.add_violation(
                    self,
                    f"Trip {trip_id} food total ({total_food}) exceeds limit {self.limit}",
                )


# =====================================================
# Rule Engine
# =====================================================

class RuleEngine:
    def __init__(self, rules: list[Rule]) -> None:
        self.rules: list[Rule] = list(rules)

    def evaluate_rule(self, expenses: list[Expense]) -> list[RuleViolation]:
        """
        Run every rule against the full expense list. Each rule decides whether
        it acts per-expense or on the aggregate.

        Time:  O(R * E)  — unavoidable when any rule may inspect any expense.
        Space: O(V)      — V = number of violations collected.
        """
        context = ValidationContext()
        for rule in self.rules:
            rule.evaluate(expenses, context)
        return context.violations


def _demo() -> None:
    # --- Coderpair-style per-expense rules ---
    per_expense_rules = [
        MaxExpenseRule(175),
        RestaurantExpenseRule(45),
        EntertainmentNotAllowedRule(),
    ]
    expenses = [
        Expense(
            expense_id="1",
            item_id="Item1",
            expense_type=ExpenseType.FOOD,
            amount=Decimal("250.00"),
            seller_type=SellerType.RESTAURANT,
            seller_name="ABC restaurant",
        ),
        Expense(
            expense_id="2",
            item_id="Item2",
            expense_type=ExpenseType.ENTERTAINMENT,
            amount=Decimal("30.00"),
            seller_type=SellerType.RESTAURANT,
            seller_name="Cinema",
        ),
        Expense(
            expense_id="3",
            item_id="Item3",
            expense_type=ExpenseType.FOOD,
            amount=Decimal("40.00"),
            seller_type=SellerType.RESTAURANT,
            seller_name="Cheap eats",
        ),
    ]

    engine: RuleEngine = RuleEngine(per_expense_rules)
    violations: list[RuleViolation] = engine.evaluate_rule(expenses)

    by_expense: dict[str, list[str]] = {}
    for v in violations:
        key = v.expense_id or "trip"
        by_expense.setdefault(key, []).append(v.rule_name)

    assert set(by_expense.get("1", [])) == {"MaxExpenseRule", "RestaurantExpenseRule"}
    assert by_expense.get("2") == ["EntertainmentNotAllowedRule"]
    assert by_expense.get("3") is None

    print("Per-expense rule violations:")
    for expense in expenses:
        failed = by_expense.get(expense.expense_id, [])
        status = "PASS" if not failed else "FAIL"
        print(f"  expense {expense.expense_id} ({expense.seller_name}): {status}")
        for v in violations:
            if v.expense_id == expense.expense_id:
                print(f"    - [{v.rule_name}] {v.message}")

    # --- Trip-level rules across TWO trips (proves per-trip grouping) ---
    # Trip TA: 600 + 60 + 50 = 710 total, 110 food
    # Trip TB: 200 + 30      = 230 total,  30 food
    trip_expenses = [
        Expense("t1", "i1", ExpenseType.TRAVEL, Decimal("600.00"), SellerType.AIRLINE, "Delta", trip_id="TA"),
        Expense("t2", "i2", ExpenseType.FOOD, Decimal("60.00"), SellerType.RESTAURANT, "Lunch", trip_id="TA"),
        Expense("t3", "i3", ExpenseType.FOOD, Decimal("50.00"), SellerType.RESTAURANT, "Dinner", trip_id="TA"),
        Expense("t4", "i4", ExpenseType.HOTEL, Decimal("200.00"), SellerType.HOTEL, "Marriott", trip_id="TB"),
        Expense("t5", "i5", ExpenseType.FOOD, Decimal("30.00"), SellerType.RESTAURANT, "Snack", trip_id="TB"),
    ]
    # Limit 700: global sum (940) would flag; per-trip only TA (710) exceeds.
    trip_engine = RuleEngine([
        TotalTripExpenseRule(700),
        TotalFoodExpenseRule(100),
    ])
    trip_violations = trip_engine.evaluate_rule(trip_expenses)

    # Only trip TA violates both rules; TB stays under both limits.
    assert len(trip_violations) == 2
    assert {v.rule_name for v in trip_violations} == {
        "TotalTripExpenseRule",
        "TotalFoodExpenseRule",
    }
    assert all(v.expense_id is None for v in trip_violations)
    assert all("TA" in v.message for v in trip_violations)

    print("\nTrip-level rule violations:")
    if not trip_violations:
        print("  PASS")
    for v in trip_violations:
        print(f"  - [{v.rule_name}] {v.message}")

    print("\nAll assertions passed ✔")


if __name__ == "__main__":
    _demo()