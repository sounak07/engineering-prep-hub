# X is-a Y -> Y is an extension of X
# Suppose there is a Base pizza and there is Margaritta, which is also a Type of Base Pizza 
# ,so its an extension of Base pizza.

# X has-a Y -> X has Y in it as a member 
# In decorator pattern suppose you have a base pizza and you want to add a topping of Extra cheese, 
# its has-a, since the New pizza(Extra cheese) will already have Base pizza in it. 
# But a Base Pizza with topping is also a pizza so it is-a pizza well.

from abc import ABC, abstractmethod


class BasePizza(ABC):
    @abstractmethod
    def get_cost(self) -> int:
        pass

# IS-A BasePizza 
class Margaritta(BasePizza):
    def get_cost(self):
        return 100

# IS-A BasePizza    
class FarmHouse(BasePizza):
    def get_cost(self):
        return 150
    
# cheese decorator | HAS-A BasePizza 
class ExtraCheese(BasePizza):
    def __init__(self, base_pizza: BasePizza):
        self.base_pizza = base_pizza

    def get_cost(self)-> int:
        return self.base_pizza.get_cost() + 100

# Pan decorator | HAS-A BasePizza
class ThickPanPizza(BasePizza):
    def __init__(self, base_pizza: BasePizza):
        self.base_pizza = base_pizza

    def get_cost(self) -> int:
        return self.base_pizza.get_cost() + 200



# buy pizza
margitta: BasePizza = Margaritta()
print('MAR', margitta.get_cost())

# extra cheese | Decorating
margitta_extra_cheese: BasePizza = ExtraCheese(margitta)
print('Extra Cheese MAR',margitta_extra_cheese.get_cost())

# extra pan mar | Decorating a decorator
margitta_extra_pan: BasePizza = ThickPanPizza(margitta_extra_cheese)
print('Extra Pan MAR', margitta_extra_pan.get_cost())

# # buy pizza
farm: BasePizza = FarmHouse()
print('FARM', farm.get_cost())

# extra pan
margitta_extra_cheese: BasePizza = ThickPanPizza(farm)
print('Extra Pan Farm',margitta_extra_cheese.get_cost())
