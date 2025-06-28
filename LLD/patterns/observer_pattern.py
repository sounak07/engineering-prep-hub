# Observer Pattern involves a observable and a observer. Observer observers the observable.
# Suppose a weather station updates weather report to devices(observer) that are observing the weather station (observable). 
# Whenever some changes occur Observable updates observers

from abc import ABC, abstractmethod


class Observer(ABC):
    @abstractmethod
    def update(self) -> None:
        pass

    @abstractmethod
    def get_id(self) -> int:
        pass

class Observable(ABC):
    @abstractmethod
    def add(self, observer: Observer) -> None:
        pass

    @abstractmethod
    def remove(self, observer_id: int) -> None:
        pass

    @abstractmethod
    def notify(self) -> None:
        pass

    @abstractmethod
    def add_item_quantity(self, quantity: int) -> None:
        pass

    @abstractmethod
    def fetch_item_quantity(self) -> int:
        pass



class DeviceObserver(Observer):
    def __init__(self, id: int ,observable_type: Observable):
        self.id = id
        self.observable = observable_type

    def get_id(self):
        return self.id

    def update(self):
        print('No of items', self.observable.fetch_item_quantity())
        

class ProductStock(Observable):
    def __init__(self):
        self.item_quantity = 0
        self.observers: list[Observer] = []

    def add(self, observer):
        self.observers.append(observer)

    def remove(self, observer_id):
        self.observers = [obv for obv in self.observers if obv.get_id() != observer_id]

    def notify(self):
        for obv in self.observers:
            obv.update()

    def add_item_quantity(self, quantity):
        if quantity == 0:
            return

        self.item_quantity += quantity
        if self.item_quantity > 0:
            self.notify()

    def fetch_item_quantity(self):
        return self.item_quantity


iphoneO = ProductStock()

wishlist = DeviceObserver(1,iphoneO)
cart = DeviceObserver(2,iphoneO)

iphoneO.add(wishlist)
iphoneO.add(cart)

iphoneO.add_item_quantity(1)
iphoneO.add_item_quantity(1)