# Abstract factory is basically a factory of factory

from abc import ABC, abstractmethod

class Car(ABC):
    @abstractmethod
    def car_name(self):
        pass

class Merc(Car):
    def car_name(self):
        return "GLA 200"
    

class BWM(Car):
    def car_name(self):
        return "M5 Competition"
    
class Tiago(Car):
    def car_name(self):
        return "TATA , desh ka loha"
    
class Creta(Car):
    def car_name(self):
        return "Chapri Car"
    

class Factory(ABC):
    @abstractmethod
    def get_car(self) -> Car:
        pass

# grping of lux cars
class LuxFactory(Factory):
    def get_car(self, car_name: str):
        if car_name == "BMW":
            return BWM()
        if car_name == "MERC":
            return Merc()

# grping of ord cars     
class OrdFactory(Factory):
    def get_car(self, car_name: str):
        if car_name == "TATA":
            return Tiago()
        if car_name == "HYUNDAI":
            return Creta()
        

class MainFactory:
    def select_car(self, car_type: str):
        if car_type == "LUXURY":
            return LuxFactory()
        if car_type == "ORD":
            return OrdFactory()
        


main_f = MainFactory()
car_f_lux = main_f.select_car("LUXURY")
bmw = car_f_lux.get_car("BMW")

car_f_ord = main_f.select_car("ORD")
tata = car_f_ord.get_car("TATA")

print("CARS for today", bmw.car_name(), ":",tata.car_name())


    



