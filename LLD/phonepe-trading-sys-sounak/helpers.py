import uuid
import time

from models import Order, OrderType


def create_buy_order(user_id: str, symbol: str, quantity: int, price: float) -> Order:

    return Order(
        order_id=str(uuid.uuid4()),
        user_id=user_id,
        order_type=OrderType.BUY,
        symbol=symbol,
        quantity=quantity,
        price=price,
        timestamp=time.time(),
    )


def create_sell_order(user_id: str, symbol: str, quantity: int, price: float) -> Order:

    return Order(
        order_id=str(uuid.uuid4()),
        user_id=user_id,
        order_type=OrderType.SELL,
        symbol=symbol,
        quantity=quantity,
        price=price,
        timestamp=time.time(),
    )
