from abc import ABC


class Vehicle(ABC):
    def get_wheel_count(self)->int:
        return 2
    

class EngineVehicle(Vehicle):
    def has_engine(self)->bool:
        return True
    

class Car(EngineVehicle):
    def get_wheel_count(self) -> int:
        return 4
    
class Truck(EngineVehicle):
    def get_wheel_count(self) -> int:
        return 6
    

# class Bicycle(Vehicle):
#     def no_of_seats(self)->int:
#         return 1
    
class Bicycle(EngineVehicle):
    def has_engine(self) -> bool:
        raise AttributeError("Has no enginee")
    

def main():
    bicycle: Vehicle = Bicycle()
    car: Vehicle = Bicycle()
    vehicles: list[Vehicle] = []
    vehicles.append(bicycle)
    vehicles.append(car)

    for v in vehicles:
        print(v.get_wheel_count())

    print("=======")

    car: EngineVehicle = Car()
    truck: EngineVehicle = Truck()
    e_vehicles: list[EngineVehicle] = []
    e_vehicles.append(truck)
    e_vehicles.append(car)

    for v in e_vehicles:
        print(v.has_engine())
        print(v.get_wheel_count())
        print("-----")

    car: EngineVehicle = Car()
    truck: EngineVehicle = Truck()
    # this will throw an AttributeError so it violates the LSP, we should not have to implement engine is Bicycle, which also violets ISP
    # so we have Vehicle class to implement Bicycle with 
    bicycle: EngineVehicle = Bicycle()
    e_vehicles: list[EngineVehicle] = []
    e_vehicles.append(truck)
    e_vehicles.append(car)
    e_vehicles.append(bicycle)

    for v in e_vehicles:
        print(v.has_engine())
        print(v.get_wheel_count())
        print("-----")


main()