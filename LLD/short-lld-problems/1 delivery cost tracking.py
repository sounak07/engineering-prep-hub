"""
RIPPLING SIGNATURE PROBLEM #1 — Food / Delivery Cost Tracking System
====================================================================
A logistics company employs many drivers. The system tracks deliveries,
calculates cost, tracks payments, and answers analytics queries.

Built in 3 escalating parts (as asked in the real interview):
  Part 1: add_driver / record_delivery / get_total_cost
  Part 2: pay_up_to / get_unpaid_amount
  Part 3: max_simultaneous_drivers_in_past_24_hours

Interview API aliases (same methods):
  AddDriver          -> add_driver
  RecordDelivery     -> record_delivery
  AddDelivery        -> record_delivery
  PayUpto            -> pay_up_to
  getTotalUnpaid     -> get_unpaid_amount

MONEY / PRECISION (the crux of this interview)
----------------------------------------------
Formula:  payout = hourly_rate * (end - start) / 3600   at 1-second precision.

Why Decimal, NOT float/double (the simple version):
  Computers store floats in BINARY (base-2), but money is BASE-10. Simple
  decimals like 0.1 can't be written exactly in binary, so the computer keeps a
  tiny approximation. Consequences:
    * 0.1 + 0.2  ->  0.30000000000000004   (not 0.3)
    * errors pile up as you sum many values
    * a balance that should be exactly 0 comes out 0.0000..1, so `== 0` fails
      (this is the "0.005 when it should be 0" bug)
  Decimal stores real base-10 digits, so a cent is exactly a cent:
    * Decimal("0.30") - Decimal("0.10") - Decimal("0.20") == Decimal("0.00")

Two rules that keep it clean:
  1. Build decimals from STRINGS, never floats: Decimal("0.1") is exact,
     Decimal(0.1) copies in the float error.
  2. Keep full precision while calculating; round to 2 decimals ONLY at the end
     (display/read time). Rounding each item then summing accumulates error.
     Here: accumulate exact `rate * seconds`, divide by 3600 + round in the getter.

Rounding mode (pick one explicitly):
  * ROUND_HALF_UP   -> a half rounds away from zero (0.005 -> 0.01). Intuitive
                       for real money; what people expect.
  * ROUND_HALF_EVEN -> "banker's rounding": a half rounds to the nearest even
                       digit (0.005 -> 0.00, 0.015 -> 0.02). Avoids upward bias
                       over millions of roundings; the accounting default.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR

CENTS = Decimal("0.01")          # money is a dollar value with 2 decimal places
_HOUR = Decimal(SECONDS_PER_HOUR)


def to_money(amount: Decimal) -> Decimal:
    """
    Round an exact Decimal to real-money precision: 2 decimal places.
    Rounding is applied ONCE, here at the boundary — never on intermediates.
    ROUND_HALF_UP: 0.005 -> 0.01, and an exact 0 stays 0.00.
    """
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class Delivery:
    driver_id: str
    start: int  # whole seconds
    end: int    # whole seconds
    rate_seconds: Decimal  # EXACT: hourly_rate * duration; divide by 3600 at read time
    paid: bool = field(default=False)

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("end time must be > start time")

    @property
    def duration(self) -> int:
        return self.end - self.start


class DeliverySystem:
    def __init__(self):
        self._driver_rate: dict[str, Decimal] = {}   # driver_id -> $/hour (exact Decimal)
        self._deliveries: list[Delivery] = []
        # Accumulators stay EXACT and unrounded (in "rate*seconds" units).
        self._total_rate_seconds = Decimal(0)
        self._unpaid_rate_seconds = Decimal(0)
        self._unpaid_by_end: list[tuple[int, int, Delivery]] = []  # (end, seq, delivery)
        self._seq = 0

    # ---------- Part 1 ----------
    def add_driver(self, driver_id: str, hourly_rate_usd) -> None:
        """
        Register a driver with an hourly rate. O(1).
        Convert via str() so a passed-in float (e.g. 36.1) doesn't smuggle in
        binary error: Decimal(36.1) is 36.100000000000001..., Decimal("36.1") is exact.
        """
        rate = Decimal(str(hourly_rate_usd))
        if rate <= 0:
            raise ValueError("hourly rate must be positive")
        self._driver_rate[driver_id] = rate

    def record_delivery(self, driver_id: str, start: int, end: int) -> Delivery:
        """
        Record a completed delivery for an existing driver. O(log n) heap push.
        Stores EXACT rate*seconds; the /3600 is deferred to read time.
        """
        if driver_id not in self._driver_rate:
            raise ValueError(f"unknown driver: {driver_id}")

        rate = self._driver_rate[driver_id]
        rate_seconds = rate * (end - start)   # exact Decimal, no division yet

        delivery = Delivery(driver_id, start, end, rate_seconds)
        self._deliveries.append(delivery)
        self._total_rate_seconds += rate_seconds
        self._unpaid_rate_seconds += rate_seconds

        self._seq += 1
        heapq.heappush(self._unpaid_by_end, (end, self._seq, delivery))
        return delivery

    # Interview alias
    add_delivery = record_delivery

    def get_total_cost(self) -> Decimal:
        """Total payout across all deliveries, rounded to cents once. O(1)."""
        return to_money(self._total_rate_seconds / _HOUR)

    # ---------- Part 2 ----------
    def pay_up_to(self, up_to_time: int) -> None:
        """
        Mark every delivery that FINISHED at or before up_to_time as paid.
        Idempotent: calling again with the same or earlier time is a no-op.
        Amortized O(k log n) where k = newly paid deliveries (heap pop).
        """
        while self._unpaid_by_end and self._unpaid_by_end[0][0] <= up_to_time:
            _, _, delivery = heapq.heappop(self._unpaid_by_end)
            if delivery.paid:
                continue
            delivery.paid = True
            self._unpaid_rate_seconds -= delivery.rate_seconds

    def get_unpaid_amount(self) -> Decimal:
        """Outstanding (unpaid) cost, rounded to cents once. O(1)."""
        return to_money(self._unpaid_rate_seconds / _HOUR)

    # ---------- Part 3 ----------
    def max_simultaneous_drivers_in_past_24_hours(self, current_time: int) -> int:
        """
        Max drivers simultaneously delivering in [current_time - 24h, current_time].

        Sweep line: +1 at (clamped) start, -1 at (clamped) end, track peak.
        Assumes one delivery at a time per driver (concurrent delivery == active driver).

        Time:  O(k log k) where k = deliveries overlapping the window
        Space: O(k)
        """
        window_start = current_time - SECONDS_PER_DAY
        events: list[tuple[int, int]] = []
        for delivery in self._deliveries:
            start = max(delivery.start, window_start)
            end = min(delivery.end, current_time)
            if start < end:
                events.append((start, 1))
                events.append((end, -1))

        events.sort(key=lambda x: (x[0], x[1]))  # -1 before +1 at same timestamp

        active = peak = 0
        for _, delta in events:
            active += delta
            peak = max(peak, active)
        return peak

    get_max_active_drivers_in_last_24_hours = max_simultaneous_drivers_in_past_24_hours

    def max_simultaneous_distinct_drivers_in_past_24_hours(self, current_time: int) -> int:
        """
        Like the above, but a driver who runs OVERLAPPING deliveries counts once.

        Difference: the plain sweep counts concurrent *deliveries*. If one driver
        has two overlapping deliveries, that's still ONE active driver. So we first
        merge each driver's own intervals (union of their active time), then sweep
        over the merged intervals — each driver contributes +1 at most at any instant.

        Time:  O(k log k)  (per-driver sort/merge sums to k; final sort is k log k)
        Space: O(k)        where k = deliveries overlapping the window
        """
        window_start = current_time - SECONDS_PER_DAY

        # 1) group each driver's clamped intervals
        by_driver: dict[str, list[tuple[int, int]]] = {}
        for delivery in self._deliveries:
            start = max(delivery.start, window_start)
            end = min(delivery.end, current_time)
            if start < end:
                by_driver.setdefault(delivery.driver_id, []).append((start, end))

        # 2) merge per driver, then emit sweep events on the union intervals
        events: list[tuple[int, int]] = []
        for intervals in by_driver.values():
            for start, end in self._merge_intervals(intervals):
                events.append((start, 1))
                events.append((end, -1))

        events.sort(key=lambda x: (x[0], x[1]))  # -1 before +1 at same timestamp

        active = peak = 0
        for _, delta in events:
            active += delta
            peak = max(peak, active)
        return peak

    @staticmethod
    def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Merge overlapping/touching [start, end) intervals. O(m log m)."""
        merged: list[list[int]] = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1]:   # overlaps/touches previous
                merged[-1][1] = max(merged[-1][1], end)  # stretch its end
            else:
                merged.append([start, end])              # gap -> new interval
        return [(start, end) for start, end in merged]


# ---------------------------------------------------------------------------
# FOLLOW-UPS to mention out loud (don't code unless asked):
#   * Why not "integer cents"? Works when every payout lands on a whole cent,
#     but rate*seconds/3600 often doesn't (e.g. $10/hr for 1s = $0.002777...).
#     Exact-Decimal accumulator + round-once avoids both float error AND the
#     "which cent does a fraction belong to" problem.
#   * Rounding policy is a business decision: ROUND_HALF_UP vs banker's
#     ROUND_HALF_EVEN. State the choice; be consistent.
#   * pay_up_to: min-heap by end-time vs O(n) scan each call.
#   * Overlapping deliveries per driver -> merge intervals before the sweep
#     (implemented: max_simultaneous_distinct_drivers_in_past_24_hours).
# ---------------------------------------------------------------------------


def _demo():
    sys = DeliverySystem()
    sys.add_driver("d1", 36.0)                   # $36/hr -> exactly $0.01/sec
    sys.add_driver("d2", 36.0)
    sys.record_delivery("d1", 0, 100)            # 100s -> $1.00
    sys.record_delivery("d2", 50, 150)           # 100s -> $1.00
    sys.record_delivery("d1", 200, 260)          # 60s  -> $0.60
    assert sys.get_total_cost() == Decimal("2.60"), sys.get_total_cost()

    sys.pay_up_to(160)                           # pays deliveries ending by t=160
    assert sys.get_unpaid_amount() == Decimal("0.60"), sys.get_unpaid_amount()

    # d1 and d2 overlap in [50,100] -> peak 2
    peak = sys.max_simultaneous_drivers_in_past_24_hours(current_time=300)
    assert peak == 2, peak

    # Idempotent pay
    before = sys.get_unpaid_amount()
    sys.pay_up_to(160)
    assert sys.get_unpaid_amount() == before

    # Unknown driver rejected
    try:
        sys.record_delivery("unknown", 0, 10)
        raise AssertionError("expected ValueError for unknown driver")
    except ValueError:
        pass

    # --- distinct-driver counting: one driver with OVERLAPPING deliveries ---
    ov = DeliverySystem()
    ov.add_driver("solo", 36.0)
    ov.record_delivery("solo", 0, 100)     # these two overlap in [50,100]
    ov.record_delivery("solo", 50, 150)
    # Plain sweep counts 2 concurrent *deliveries*...
    assert ov.max_simultaneous_drivers_in_past_24_hours(300) == 2
    # ...but it's the SAME driver, so distinct-driver count is 1.
    assert ov.max_simultaneous_distinct_drivers_in_past_24_hours(300) == 1

    # two distinct drivers overlapping -> both variants agree on 2
    ov.add_driver("other", 36.0)
    ov.record_delivery("other", 60, 120)
    assert ov.max_simultaneous_distinct_drivers_in_past_24_hours(300) == 2

    # --- precision stress test: the "should be 0.00, not 0.005" scenario ---
    # $10/hr => each second is $0.002777... (NOT a whole cent).
    prec = DeliverySystem()
    prec.add_driver("p", 10.0)
    # 360 one-second deliveries. Exact total = 10 * 360 / 3600 = $1.00 exactly.
    # Float per-second rounding would drift; exact accumulation lands on 1.00.
    for t in range(360):
        prec.record_delivery("p", t, t + 1)
    assert prec.get_total_cost() == Decimal("1.00"), prec.get_total_cost()

    # Pay everything -> unpaid must be EXACTLY 0.00, never 0.005.
    prec.pay_up_to(360)
    assert prec.get_unpaid_amount() == Decimal("0.00"), prec.get_unpaid_amount()

    print("get_total_cost        ->", sys.get_total_cost())
    print("get_unpaid_amount     ->", sys.get_unpaid_amount())
    print("max_simultaneous (24h)->", peak)
    print("precision total       ->", prec.get_total_cost())
    print("precision unpaid      ->", prec.get_unpaid_amount())
    print("All assertions passed ✔")


if __name__ == "__main__":
    _demo()
