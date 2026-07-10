from main import TradeManager, User, OrderStatus, create_buy_order, create_sell_order


def setup_engine() -> TradeManager:
    engine = TradeManager()
    user1 = User(user_id="U1", name="Alice", phone="1111111111", email="alice@test.com")
    user2 = User(user_id="U2", name="Bob", phone="2222222222", email="bob@test.com")

    engine.register_user(user1)
    engine.register_user(user2)

    return engine


def test_order_matching() -> None:
    engine = setup_engine()
    buy_order = create_buy_order(
        user_id="U1", symbol="RELIANCE", quantity=10, price=100
    )
    sell_order = create_sell_order(
        user_id="U2", symbol="RELIANCE", quantity=10, price=95
    )
    engine.place_order(buy_order)
    engine.place_order(sell_order)

    engine.command_queue.join()
    assert len(engine.trades) == 1
    trade = engine.trades[0]

    assert trade.quantity == 10
    assert trade.price == 95

    assert buy_order.status == OrderStatus.EXECUTED
    assert sell_order.status == OrderStatus.EXECUTED

    engine.shutdown()


def test_order_cancellation() -> None:
    engine = setup_engine()
    buy_order = create_buy_order(user_id="U1", symbol="TCS", quantity=10, price=100)
    engine.place_order(buy_order)
    engine.command_queue.join()
    engine.cancel_order(buy_order.order_id)
    engine.command_queue.join()
    assert buy_order.status == OrderStatus.CANCELLED
    engine.shutdown()


def test_order_modification() -> None:
    engine = setup_engine()
    buy_order = create_buy_order(user_id="U1", symbol="INFY", quantity=10, price=100)
    engine.place_order(buy_order)
    engine.command_queue.join()
    engine.modify_order(order_id=buy_order.order_id, quatity=20, price=120)
    engine.command_queue.join()

    assert buy_order.quantity == 20
    assert buy_order.price == 120
    engine.shutdown()


def test_invalid_user_order_rejected() -> None:
    engine = setup_engine()
    invalid_order = create_buy_order(
        user_id="INVALID_USER", symbol="WIPRO", quantity=10, price=100
    )
    engine.place_order(invalid_order)
    engine.command_queue.join()
    assert invalid_order.status == OrderStatus.REJECTED
    engine.shutdown()


def test_partial_fill() -> None:
    engine = setup_engine()
    buy_order = create_buy_order(user_id="U1", symbol="HDFC", quantity=20, price=100)
    sell_order = create_sell_order(user_id="U2", symbol="HDFC", quantity=10, price=95)
    engine.place_order(buy_order)
    engine.place_order(sell_order)
    engine.command_queue.join()

    assert len(engine.trades) == 1
    assert buy_order.status == OrderStatus.PARTIAL
    assert sell_order.status == OrderStatus.EXECUTED
    assert buy_order.quantity == 10

    engine.shutdown()


def test_order_book_per_symbol() -> None:
    engine = setup_engine()

    reliance_order = create_buy_order(
        user_id="U1", symbol="RELIANCE", quantity=10, price=100
    )
    tcs_order = create_buy_order(user_id="U1", symbol="TCS", quantity=20, price=200)

    engine.place_order(reliance_order)
    engine.place_order(tcs_order)

    engine.command_queue.join()

    assert "RELIANCE" in engine.order_books
    assert "TCS" in engine.order_books

    reliance_book = engine.order_books["RELIANCE"]
    tcs_book = engine.order_books["TCS"]

    assert len(reliance_book.buy_orders) == 1
    assert len(tcs_book.buy_orders) == 1

    assert reliance_book.buy_orders[0].symbol == "RELIANCE"
    assert tcs_book.buy_orders[0].symbol == "TCS"
    assert reliance_book.buy_orders[0].order_id != tcs_book.buy_orders[0].order_id
    engine.shutdown()
