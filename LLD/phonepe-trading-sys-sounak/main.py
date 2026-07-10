import heapq
import time

from queue import Queue
from models import Order, OrderStatus, Trade, User
from abc import ABC, abstractmethod
from state_machine import StateMachineOperator
from threading import Thread
from helpers import create_buy_order, create_sell_order
from matching_strategy import OrderBook, MatchingStrategy, PriceTimePriorityStrategy


class ValidationHandler(ABC):
    def __init__(self, next_handler: "ValidationHandler" = None) -> None:
        self.next_handler = next_handler

    @abstractmethod
    def handle(self, order: Order, engine: "TradeManager") -> bool:
        pass

    def next(self, order: Order, engine: "TradeManager") -> bool:
        if self.next_handler:
            return self.next_handler.handle(order, engine)

        return True


class UserHandler(ValidationHandler):
    def handle(self, order: Order, engine: "TradeManager") -> bool:
        if order.user_id not in engine.users:
            raise Exception("User does not exisit")

        return self.next(order, engine)


class QuantityHanlder(ValidationHandler):
    def handle(self, order: Order, engine: "TradeManager") -> bool:
        if order.quantity <= 0:
            raise Exception("Invalid quantity")

        return self.next(order, engine)


class PriceHandler(ValidationHandler):
    def handle(self, order: Order, engine: "TradeManager") -> bool:
        if order.price <= 0:
            raise Exception("Invalid price")

        return self.next(order, engine)


class Command(ABC):
    @abstractmethod
    def execute(self, engine: "TradeManager") -> None:
        pass


class PlaceOrder(Command):
    def __init__(self, order: Order) -> None:
        self.order: Order = order

    def execute(self, engine: "TradeManager") -> None:
        order: Order = self.order
        try:
            engine.validator.handle(self.order, engine)
            engine.orders[order.order_id] = order

            if order.symbol not in engine.order_books:
                engine.order_books[order.symbol] = OrderBook(
                    order.symbol, engine.matching_strategy
                )

            book: OrderBook = engine.order_books[order.symbol]

            with book._lock:
                book.add_order(order)
                book.match_orders(engine.trades)

            print(f"Order accepted == {order.order_id}")
        except Exception as e:
            order.status = OrderStatus.REJECTED
            print(f"Order rejected due to {e}")


class CancelOrder(Command):
    def __init__(self, order_id: str) -> None:
        self.order_id: Order = order_id

    def execute(self, engine: "TradeManager") -> None:
        try:
            order: Order | None = engine.orders.get(self.order_id)

            if not order:
                print("No order found")
                return

            if order.status in (OrderStatus.CANCELLED, OrderStatus.EXECUTED):
                print("Order cancelled or already executed")
                return

            StateMachineOperator.transit(order, OrderStatus.CANCELLED)

            print(f"Order cancelled == {order.order_id}")
        except Exception as e:
            order.status = OrderStatus.REJECTED
            print(f"Order rejected due to {e}")


class ModifyOrder(Command):
    def __init__(self, order_id: str, quantity: int, price: float) -> None:
        self.order_id: str = order_id
        self.quantity: int = quantity
        self.price: float = price

    def execute(self, engine: "TradeManager") -> None:
        try:
            order: Order | None = engine.orders.get(self.order_id)

            if not order:
                print("No order found")
                return

            if order.status in (OrderStatus.CANCELLED, OrderStatus.EXECUTED):
                print("Order cancelled or already executed")
                return

            book: OrderBook = engine.order_books[order.symbol]

            with book._lock:
                order.quantity = self.quantity
                order.price = self.price
                order.timestamp = time.time()

                order.update_index()
                heapq.heapify(book.buy_orders)
                heapq.heapify(book.sell_orders)
                book.match_orders(engine.trades)

            print(f"Order modified == {order.order_id}")
        except Exception as e:
            order.status = OrderStatus.REJECTED
            print(f"Order rejected due to {e}")


class TradeManager:
    def __init__(self, queue_size: int = 100) -> None:
        self.command_queue: Queue = Queue(maxsize=queue_size)
        self.users: dict[str, User] = {}
        self.orders: dict[str, Order] = {}
        self.trades: list[Trade] = []
        self.matching_strategy: MatchingStrategy = PriceTimePriorityStrategy()
        self.order_books: dict[str, OrderBook] = {}

        self.validator: ValidationHandler = UserHandler(QuantityHanlder(PriceHandler()))
        self.running: bool = True
        self.matching_thread: Thread = Thread(target=self._run_matching_engine)

        self.matching_thread.daemon = True
        self.matching_thread.start()

    def register_user(self, user: User) -> None:

        self.users[user.user_id] = user

    def place_order(self, order: Order) -> None:
        print(f"Queuing Order {order.order_id}")
        self.command_queue.put(PlaceOrder(order))

    def cancel_order(self, order_id: str) -> None:
        print(f"Queuing Order {order_id}")
        self.command_queue.put(CancelOrder(order_id))

    def modify_order(self, order_id: str, quatity: int, price: int) -> None:
        print(f"Queuing Order {order_id}")
        self.command_queue.put(ModifyOrder(order_id, quantity=quatity, price=price))

    def get_order_status(self, order_id: str) -> str | OrderStatus:
        order: Order | None = self.orders.get(order_id, None)
        if not order:
            return "Not found"

        return order.status

    def _run_matching_engine(self) -> None:

        while self.running:
            command: Command = self.command_queue.get()
            try:
                command.execute(self)
            finally:
                self.command_queue.task_done()

    def shutdown(self) -> None:
        self.running = False
        self.matching_thread.join(timeout=1)


def demo_service():
    def buy_producer() -> None:
        for _ in range(5):
            order: Order = create_buy_order(
                user_id="U1", symbol="RELIANCE", quantity=10, price=100
            )
            engine.place_order(order)
            time.sleep(0.5)

    def sell_producer() -> None:
        for _ in range(5):
            order: Order = create_sell_order(
                user_id="U2", symbol="RELIANCE", quantity=10, price=95
            )
            engine.place_order(order)
            time.sleep(0.5)

    engine: TradeManager = TradeManager(queue_size=5)
    user1: User = User(
        user_id="U1", name="Alice", phone="1111111111", email="alice@test.com"
    )

    user2: User = User(
        user_id="U2", name="Bob", phone="2222222222", email="bob@test.com"
    )

    engine.register_user(user1)
    engine.register_user(user2)
    t1: Thread = Thread(target=buy_producer)
    t2: Thread = Thread(target=sell_producer)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
    engine.command_queue.join()

    print("\n===================")
    print("FINAL TRADES")
    print("===================\n")

    for trade in engine.trades:
        print(trade)

    print("\n===================")
    print("FINAL ORDER STATUS")
    print("===================\n")

    for order_id, order in engine.orders.items():
        print(order_id, order.status)

    engine.shutdown()


if __name__ == "__main__":
    demo_service()
