# https://www.lldcoding.com/design-lld-a-parking-lot-machine-coding-interview

# We will focus on the following set of requirements while designing the parking lot:

# The parking lot should have multiple floors where customers can park their cars.

# The parking lot should have multiple entry and exit points.

# Customers can collect a parking ticket from the entry points and can pay the parking fee at the exit points on their way out.

# Customers can pay the tickets at the automated exit panel or to the parking attendant.

# Customers can pay via both cash and credit cards.

# Customers should also be able to pay the parking fee at the customer’s info portal on each floor. If the customer has paid at the info portal, they don’t have to pay at the exit.

# The system should not allow more vehicles than the maximum capacity of the parking lot. If the parking is full, the system should be able to show a message at the entrance panel and on the parking display board on the ground floor.

# Each parking floor will have many parking spots. The system should support multiple types of parking spots such as Compact, Large, Handicapped, Motorcycle, etc.

# The Parking lot should have some parking spots specified for electric cars. These spots should have an electric panel through which customers can pay and charge their vehicles.

# The system should support parking for different types of vehicles like car, truck, van, motorcycle, etc.

# Each parking floor should have a display board showing any free parking spot for each spot type.

# The system should support a per-hour parking fee model. For example, customers have to pay $4 for the first hour, $3.5 for the second and third hours, and $2.5 for all the remaining hours.

# Enums for VehicleType, ParkingSpotType, AccountStatus, ParkingTicketStatus
from enum import Enum
from abc import ABC, abstractmethod
import time
import threading


class VehicleType(Enum):
    CAR = "Car"
    TRUCK = "Truck"
    ELECTRIC = "Electric Car"
    VAN = "Van"
    MOTORBIKE = "Motorbike"

    def can_fit_in_spot(self, spot_type):
        if self in [VehicleType.TRUCK, VehicleType.VAN]:
            return spot_type == ParkingSpotType.LARGE
        elif self == VehicleType.MOTORBIKE:
            return spot_type == ParkingSpotType.MOTORBIKE
        elif self == VehicleType.CAR:
            return spot_type in [ParkingSpotType.COMPACT, ParkingSpotType.LARGE]
        elif self == VehicleType.ELECTRIC:
            return spot_type in [
                ParkingSpotType.ELECTRIC,
                ParkingSpotType.COMPACT,
                ParkingSpotType.LARGE,
            ]
        return False


class ParkingSpotType(Enum):
    HANDICAPPED = "Handicapped"
    COMPACT = "Compact"
    LARGE = "Large"
    MOTORBIKE = "Motorbike"
    ELECTRIC = "Electric Charging"

    def is_suitable_for(self, vehicle_type):
        return vehicle_type.can_fit_in_spot(self)


class ParkingTicketStatus(Enum):
    ACTIVE = "Ticket Active"
    PAID = "Ticket Paid"
    LOST = "Ticket Lost"

    def is_paid(self):
        return self == ParkingTicketStatus.PAID


# TODO - add observer pattern for parking spot updates


class Observer(ABC):
    def __init__(self, vehicle_type: VehicleType):
        self.vehicle_type = vehicle_type

    @abstractmethod
    def update(self, message: str):
        pass


class DisplayBoard(Observer):
    def __init__(self, vehicle_type: VehicleType):
        super().__init__(vehicle_type)

    def update(self, message: str):
        print(f"Display Board Update: {message}")


class UserNotification(Observer):
    def __init__(self, vehicle_type: VehicleType):
        super().__init__(vehicle_type)

    def update(self, message: str):
        print(f"User Notification: {message}")


# Minimal Vehicle class and subtypes
class Vehicle:
    def __init__(self, vehicle_type):
        self.vehicle_type = vehicle_type
        self.ticket = None

    def assign_ticket(self, ticket):
        self.ticket = ticket

    def get_vehicle_type(self):
        return self.vehicle_type

    def get_vehicle_type_name(self):
        return self.vehicle_type.name


class Car(Vehicle):
    def __init__(self):
        super().__init__(VehicleType.CAR)


class Truck(Vehicle):
    def __init__(self):
        super().__init__(VehicleType.TRUCK)


class EV(Vehicle):
    def __init__(self):
        super().__init__(VehicleType.ELECTRIC)


# Factory Method for creating vehicles
class VehicleFactory:
    @staticmethod
    def create_vehicle(vehicle_type: VehicleType) -> Vehicle:
        if vehicle_type == VehicleType.CAR:
            return Car()
        elif vehicle_type == VehicleType.TRUCK:
            return Truck()
        elif vehicle_type == VehicleType.ELECTRIC:
            return EV()
        else:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")


# Template Method Pattern
class ParkingSpot:
    def __init__(
        self, spot_id: int, spot_type: ParkingSpotType = ParkingSpotType.LARGE
    ):
        self.spot_type = spot_type
        self.spot_id = f"SPOT-{spot_id}"
        self.parked_vehicle: Vehicle = None
        self.lock = threading.Lock()

    def get_type(self):
        return self.spot_type

    def update_spot_type(self, spot_type: ParkingSpotType):
        self.spot_type = spot_type

    def get_parked_vehicle(self):
        return self.parked_vehicle

    def set_spot_type(self, spot_type: ParkingSpotType):
        self.spot_type = spot_type

    def get_spot_id(self):
        return self.spot_id

    def is_available(self):
        return self.parked_vehicle is None

    def park_vehicle(self, vehicle: Vehicle) -> bool:
        with self.lock:
            if not self.is_available():
                print("Spot is already occupied")
                return False

            if not self.spot_type.is_suitable_for(vehicle.vehicle_type):
                print(
                    f"Vehicle type {vehicle.vehicle_type} cannot fit in spot type {self.spot_type}"
                )
                return False

            self.parked_vehicle = vehicle
            return True

    def unpark_vehicle(self, vehicle: Vehicle) -> bool:
        with self.lock:
            if self.is_available():
                raise Exception("Spot is already free")

            if self.parked_vehicle.get_vehicle_type() != vehicle.get_vehicle_type():
                raise Exception(
                    f"Vehicle type {vehicle.get_vehicle_type()} does not match parked vehicle type {self.parked_vehicle.get_vehicle_type()}"
                )

            self.parked_vehicle = None
            return True


# Placeholder classes
class ParkingTicket:
    _id = 0

    def __init__(self):
        ParkingTicket._id += 1
        self.ticket_number = f"TICKET-{ParkingTicket._id}"
        self.status = ParkingTicketStatus.ACTIVE
        self.time = time.time()  # Store the time of ticket creation

    def save_in_db(self):
        pass

    def update_status(self, status):
        self.status = status

    def get_status(self):
        return self.status


class Level:
    def __init__(
        self,
        level_number: int,
        parking_spots: int,
        parking_spot_type: ParkingSpotType = ParkingSpotType.LARGE,
    ):
        self.level_number = level_number
        self.parking_spots = [
            ParkingSpot(i, parking_spot_type) for i in range(parking_spots)
        ]

    def park_vehicle(self, vehicle: Vehicle):
        for spot in self.parking_spots:
            if spot.is_available() and spot.park_vehicle(vehicle):
                return True
        return False

    def get_available_parking_spots(self, vehicle_type: VehicleType) -> list[dict]:
        available_spots = [
            {
                "spot_type": spot.get_type(),
                "floor_number": self.level_number,
            }
            for spot in self.parking_spots
            if spot.is_available() and spot.get_type().is_suitable_for(vehicle_type)
        ]
        return available_spots

    def unpark_vehicle(self, vehicle: Vehicle) -> bool:
        for spot in self.parking_spots:
            if (
                not spot.is_available()
                and spot.get_parked_vehicle() == vehicle
                and spot.unpark_vehicle(vehicle)
            ):
                return True
        return False

    def display_available_spots(self):
        print(f"Available spots on level {self.level_number}:\n")
        for spot in self.parking_spots:
            print(
                f"Spot ID: {spot.get_spot_id()} of Type: {spot.get_type()} is {'Free' if spot.is_available() else 'Occupied'}"
            )


class HandicappedSpot(ParkingSpot):
    def __init__(self):
        super().__init__(ParkingSpotType.HANDICAPPED)


class CompactSpot(ParkingSpot):
    def __init__(self):
        super().__init__(ParkingSpotType.COMPACT)


class LargeSpot(ParkingSpot):
    def __init__(self):
        super().__init__(ParkingSpotType.LARGE)


# Factory Method Pattern for creating parking spots
class ParkingSpotFactory:
    @staticmethod
    def create_parking_spot(spot_type: ParkingSpotType) -> ParkingSpot:
        if spot_type == ParkingSpotType.HANDICAPPED:
            return HandicappedSpot()
        elif spot_type == ParkingSpotType.COMPACT:
            return CompactSpot()
        elif spot_type == ParkingSpotType.LARGE:
            return LargeSpot()
        elif spot_type == ParkingSpotType.MOTORBIKE:
            return ParkingSpot(ParkingSpotType.MOTORBIKE)
        elif spot_type == ParkingSpotType.ELECTRIC:
            return ParkingSpot(ParkingSpotType.ELECTRIC)
        else:
            raise ValueError(f"Unknown parking spot type: {spot_type}")


# Strategy Pattern
class PaymentStrategy:
    def pay(self, ticket: ParkingTicket, amount: float):
        raise NotImplementedError


class CashPaymentStrategy(PaymentStrategy):
    def pay(self, ticket: ParkingTicket, amount: float):
        print(
            f"Processing cash payment for ticket: {ticket.ticket_number} , amount: ${amount:.2f}"
        )
        return True


class CreditCardPaymentStrategy(PaymentStrategy):
    def pay(self, ticket: ParkingTicket, amount: float):
        print(
            f"Processing credit card payment for ticket: {ticket.ticket_number} , amount: ${amount:.2f}"
        )
        return True


class TicketManager:
    def __init__(self):
        self.tickets = {}
        self.lock = threading.Lock()

    @staticmethod
    def calculate_parking_fee(hours_parked: int, parking_rate: float) -> float:
        if hours_parked <= 1:
            return parking_rate
        return parking_rate * hours_parked

    def create_ticket(self) -> ParkingTicket:
        ticket = ParkingTicket()
        ticket.save_in_db()
        with self.lock:
            self.tickets[ticket.ticket_number] = ticket
        return ticket

    def get_ticket(self, ticket_number: str) -> ParkingTicket:
        with self.lock:
            return self.tickets.get(ticket_number)

    def update_ticket_status(self, ticket_number: str, status: ParkingTicketStatus):
        with self.lock:
            if ticket_number in self.tickets:
                self.tickets[ticket_number].update_status(status)
                print(
                    f"Ticket {ticket_number} updated status :{self.tickets[ticket_number].get_status()}"
                )

    def remove_ticket(self, ticket_number: str):
        with self.lock:
            if ticket_number in self.tickets:
                del self.tickets[ticket_number]

    def process_ticket_fee(self, parking_ticket: ParkingTicket, amount: float) -> float:
        if parking_ticket.status.is_paid():
            raise Exception("Ticket already paid")

        parked_time = time.time() - parking_ticket.time
        hours_parked = max(1, int(parked_time / 3600))
        fee = self.calculate_parking_fee(hours_parked, amount)
        return fee


class ParkingLotNotifiar:
    def __init__(self):
        self.observers: list[Observer] = []

    def add_observer(self, observer: Observer):
        self.observers.append(observer)

    def remove_observer(self, observer: Observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self, vehicle_type: VehicleType, message: str):
        for observer in self.observers:
            if observer.vehicle_type == vehicle_type:
                # Notify only observers interested in this vehicle type
                observer.update(message)


class ParkingLot:
    _instance = None
    _lock = threading.Lock()

    # Singleton Pattern to ensure only one instance of ParkingLot exists
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ParkingLot, cls).__new__(cls)
                cls._instance.__init__()
        return cls._instance

    def __init__(
        self, name="Cool Parking lot", parking_rate=4, floors=3, entrances=2, exits=2
    ):
        self.name = name
        self.parking_rate = parking_rate
        self.parking_floors: list[Level] = [Level(i, 10) for i in range(floors)]
        self.entrances = entrances
        self.exits = exits
        self.observers: list[Observer] = []
        self.ticket_manager = TicketManager()
        self.notifier = ParkingLotNotifiar()

    def is_parking_full(self, vehicle_type) -> bool:
        # Check if parking is full for the given vehicle type
        return all(
            len(floor.get_available_parking_spots(vehicle_type)) == 0
            for floor in self.parking_floors
        )

    def add_parking_floor(
        self, level_number: int, parking_spots: int, parking_spot_type: ParkingSpotType
    ):
        if level_number < len(self.parking_floors):
            raise Exception("Level number already exists")

        new_floor = Level(level_number, parking_spots, parking_spot_type)
        self.parking_floors.append(new_floor)

    def park_vehicle(self, vehicle: Vehicle):
        for floor in self.parking_floors:
            if floor.park_vehicle(vehicle):
                return True
        return False

    def unpark_vehicle(self, vehicle: Vehicle):
        for floor in self.parking_floors:
            if floor.unpark_vehicle(vehicle):
                return True
        return False

    def issue_parking_ticket(self, vehicle: Vehicle) -> ParkingTicket:
        if self.is_parking_full(vehicle.get_vehicle_type()):
            raise Exception(
                f"Parking full for vehicle type: {vehicle.get_vehicle_type()}"
            )
        if not self.park_vehicle(vehicle):
            raise Exception(
                f"Parking Error for vehicle type: {vehicle.get_vehicle_type()}"
            )
        ticket = self.ticket_manager.create_ticket()
        vehicle.assign_ticket(ticket)
        return ticket

    def set_observer(self, observer: Observer):
        self.notifier.add_observer(observer)

    def charge_vehicle_and_exit(
        self,
        vehicle: Vehicle,
        parking_ticket: ParkingTicket,
        payment_strategy: PaymentStrategy,
    ):
        fee = self.ticket_manager.process_ticket_fee(parking_ticket, self.parking_rate)
        if payment_strategy.pay(parking_ticket, fee):
            self.ticket_manager.update_ticket_status(
                parking_ticket.ticket_number, ParkingTicketStatus.PAID
            )
        self.unpark_vehicle(vehicle)
        print(f"Vehicle {vehicle.get_vehicle_type()} has exited the parking lot.")

        self.notifier.notify_observers(
            vehicle.get_vehicle_type(),
            f"Vehicle {vehicle.get_vehicle_type()} has exited. Spot is now free.",
        )


# Main
if __name__ == "__main__":
    parking_lot = ParkingLot()
    car = VehicleFactory.create_vehicle(VehicleType.CAR)
    ticket = parking_lot.issue_parking_ticket(car)
    print(
        f"Issued ticket: {ticket.ticket_number} for vehicle type: {car.get_vehicle_type_name()}"
    )
    parking_lot.set_observer(DisplayBoard(VehicleType.CAR))
    parking_lot.set_observer(UserNotification(VehicleType.MOTORBIKE))
    parking_lot.add_parking_floor(4, 10, ParkingSpotType.MOTORBIKE)
    parking_lot.charge_vehicle_and_exit(
        car,
        ticket,
        CreditCardPaymentStrategy(),
    )
