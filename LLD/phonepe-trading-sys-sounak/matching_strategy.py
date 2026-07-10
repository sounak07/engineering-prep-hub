import heapq
import heapq
import uuid
import time

from models import Order, OrderType, Trade
from threading import RLock
from models import OrderStatus, Order, Trade
from abc import ABC, abstractmethod
from state_machine import StateMachineOperator


class OrderBook:
    def __init__(self, symbol: str, strategy: "MatchingStrategy") -> None:
        self.symbol: str = symbol
        self.buy_orders: list[Order] = []
        self.sell_orders: list[Order] = []

        self.strategy: "MatchingStrategy" = strategy
        self._lock: RLock = RLock()

    def add_order(self, order: Order) -> None:
        if order.order_type == OrderType.BUY:
            heapq.heappush(self.buy_orders, order)
        else:
            heapq.heappush(self.sell_orders, order)

    def match_orders(self, trades: list[Trade]) -> None:
        self.strategy.match(self, trades)


class MatchingStrategy(ABC):
    @abstractmethod
    def match(self, order_book: OrderBook, trades: list[Trade]) -> None:
        pass


class PriceTimePriorityStrategy(MatchingStrategy):
    def match(self, order_book: OrderBook, trades: list[Trade]) -> None:

        while order_book.buy_orders and order_book.sell_orders:
            top_buy: Order = order_book.buy_orders[0]
            top_sell: Order = order_book.sell_orders[0]

            # lazy cleanup as clearing arbitrary element is expensive in heaps
            if top_buy.status == OrderStatus.CANCELLED:
                heapq.heappop(order_book.buy_orders)
                continue

            if top_sell.status == OrderStatus.CANCELLED:
                heapq.heappop(order_book.sell_orders)
                continue

            if top_buy.price < top_sell.price:
                break

            trade_q: int = min(top_buy.quantity, top_sell.quantity)
            trades.append(
                Trade(
                    trade_id=str(uuid.uuid4()),
                    buyer_order_id=top_buy.order_id,
                    seller_order_id=top_sell.order_id,
                    symbol=order_book.symbol,
                    quantity=trade_q,
                    price=top_sell.price,
                    timestamp=time.time(),
                )
            )

            print("Trade execution Success!")
            top_buy.quantity -= trade_q
            top_sell.quantity -= trade_q

            if top_buy.quantity == 0:
                StateMachineOperator.transit(top_buy, OrderStatus.EXECUTED)
                heapq.heappop(order_book.buy_orders)
            else:
                StateMachineOperator.transit(top_buy, OrderStatus.PARTIAL)

            if top_sell.quantity == 0:
                StateMachineOperator.transit(top_sell, OrderStatus.EXECUTED)
                heapq.heappop(order_book.sell_orders)
            else:
                StateMachineOperator.transit(top_sell, OrderStatus.PARTIAL)
