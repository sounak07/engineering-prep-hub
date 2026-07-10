from models import OrderStatus, Order


class StateMachineOperator:
    VALID_TRANSITIONS = {
        OrderStatus.ACCEPTED: {
            OrderStatus.PARTIAL,
            OrderStatus.CANCELLED,
            OrderStatus.EXECUTED,
        },
        OrderStatus.PARTIAL: {OrderStatus.CANCELLED, OrderStatus.EXECUTED},
    }

    @classmethod
    def transit(cls, order: Order, new_order_status: OrderStatus):
        if order.status == new_order_status:
            return

        allowed_states: OrderStatus = cls.VALID_TRANSITIONS.get(order.status, set())

        if new_order_status not in allowed_states:
            raise ValueError("Invalid order status")

        order.status = new_order_status
