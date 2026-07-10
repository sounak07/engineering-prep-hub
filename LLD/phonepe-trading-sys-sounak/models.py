from enum import Enum
from dataclasses import dataclass, field


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXECUTED = "EXECUTED"
    PARTIAL = "PARTIAL"


@dataclass
class User:
    user_id: str
    name: str
    phone: str
    email: str


@dataclass(order=True)
class Order:

    sort_index: tuple = field(init=False, repr=False)

    order_id: str
    user_id: str
    order_type: OrderType
    symbol: str
    quantity: int
    price: float
    timestamp: float

    status: OrderStatus = OrderStatus.ACCEPTED

    def update_index(self) -> None:
        if self.order_type == OrderType.BUY:
            self.sort_index = (-self.price, self.timestamp)
        else:
            self.sort_index = (self.price, self.timestamp)

    def __post_init__(self) -> None:
        self.update_index()


@dataclass
class Trade:
    trade_id: str
    buyer_order_id: str
    seller_order_id: str
    symbol: str
    quantity: int
    price: float
    timestamp: float
