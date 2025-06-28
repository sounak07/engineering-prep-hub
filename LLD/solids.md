### Single Responsibility Principle

- The SRP states that a class should have only one reason to change, meaning it should have only one responsibility. 
- This principle helps in making classes more focused and easier to understand, maintain, and test.

Example: Let's say we have a class called `User` that handles both user data storage and user authentication. This violates the SRP. Instead, we should split it into two classes: `UserStorage` for data storage and `UserAuthenticator` for authentication, each with a single responsibility.

### Open/Closed Principle (OCP)

- The OCP states that software entities (classes, modules, functions) should be open for extension but closed for modification. 
- This means that you should be able to extend the behavior of a class without changing its existing code.

Example: Consider a `Shape` class with a method called `area()` that calculates the area of different shapes. Instead of modifying the `Shape` class to add new shapes, we can create new classes like `Circle` and `Triangle`, each implementing their own `area()` method, thereby extending the functionality without modifying `Shape`.

```python
class Shape:
    def calculate_area(self):
        pass

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def calculate_area(self):
        return 3.14 * self.radius * self.radius

class Square(Shape):
    def __init__(self, side):
        self.side = side

    def calculate_area(self):
        return self.side * self.side

class AreaCalculator:
    def calculate(self, shape):
        return shape.calculate_area()

# Now, if we want to add a new shape (e.g., Triangle), we can do it without modifying existing code:
class Triangle(Shape):
    def __init__(self, base, height):
        self.base = base
        self.height = height

    def calculate_area(self):
        return 0.5 * self.base * self.height

```

```python

from abc import ABC, abstractmethod

class Invoice(ABC):

    @abstractmethod
    def save(self):
        pass

class InvoiceSavetoDB(Invoice):

	def save(self):
		# save to file

class InvoiceSavetoFile(Invoice):

	def save(self):
		# save to file

```
### Liskov Substitution Principle (LSP)

- The LSP states that objects of a superclass(parent) should be replaceable with objects of its subclasses without affecting the correctness of the program. 
- In simpler terms, a subclass should behave in a way that does not surprise the client using the superclass.
- Child class should extend the behaviour of parent and narrow it down. 

Let's say we have a class `Bird` with a method `fly()`. Now, we create a subclass called `Penguin` that also extends `Bird`. The `Penguin` class should not have the `fly()` method, or it should throw an exception if called. Otherwise, it would violate the LSP since calling `fly()` on a `Penguin` instance wouldn't behave as expected.

```python
class Bird:
    def fly(self):
        pass

class Sparrow(Bird):
    def fly(self):
        return "Sparrow flying high"

class Penguin(Bird):
    def fly(self):
        raise NotImplementedError("Penguins can't fly")

# Usage without surprises:
def let_bird_fly(bird):
    print(bird.fly())

sparrow = Sparrow()
penguin = Penguin()

let_bird_fly(sparrow)  # Output: "Sparrow flying high"
let_bird_fly(penguin)  # Throws an exception as expected

```

### Interface Segregation Principle (ISP)

- The ISP states that a class should not be forced to implement interfaces it does not use. Instead of having a large, monolithic interface, it's better to have smaller and more specific interfaces that clients can implement selectively.

Example: Consider an interface called `Printer` with methods `print()` and `scan()`. If a class only needs printing functionality and not scanning, implementing the `scan()` method would be unnecessary. Instead, we can create two separate interfaces, `Printable` and `Scannable`, to segregate the responsibilities.

```python
class Printer:
    def print_document(self):
        pass

class Scanner:
    def scan_document(self):
        pass

class Photocopier(Printer, Scanner):
    def print_document(self):
        print("Photocopier printing")

    def scan_document(self):
        print("Photocopier scanning")

```

### Dependency Inversion Principle (DIP)

The DIP states that high-level modules should not depend on low-level modules. Both should depend on abstractions. In other words, classes should rely on interfaces or abstract classes, not concrete implementations.

Example: Suppose we have a class `OrderProcessor` that directly depends on a concrete class `DatabaseOrderRepository` to fetch order data. Instead, `OrderProcessor` should depend on an interface like `OrderRepository`, and the `DatabaseOrderRepository` class should implement that interface. This way, we can easily switch to a different data storage solution without modifying `OrderProcessor`.

```python
class OrderRepository:
    def save(self, order):
        pass

class FileOrderRepository(OrderRepository):
    def save(self, order):
        print("Saving order to file")
        
class DatabaseOrderRepository(OrderRepository):
    def save(self, order):
        print("Saving order to db")
        
class OrderProcessor:
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    def process_order(self, order):
        self.order_repository.save(order)

# Client code using the dependency inversion principle:
database_repo = DatabaseOrderRepository()
file_repo = FileOrderRepository()

order_processor_with_database = OrderProcessor(database_repo)
order_processor_with_file = OrderProcessor(file_repo)

order_processor_with_database.process_order(order_data)
order_processor_with_file.process_order(order_data)

```

