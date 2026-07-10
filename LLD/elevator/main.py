"""
Design an elevator control system for a building. 
The system should handle multiple elevators, floor requests, and move elevators efficiently to service requests.

Questions?

Requirements
- How many floors? 
- users can make requests for hall and request for a floor 
- passengers can select multiple floors

Error handling
- entering floor that is not present
- pressing the same floor the user is in

"""

from __future__ import annotations

from enum import Enum
from typing import Set

class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    IDLE = "IDLE"

class RequestType:
    PICKUP_UP = "PICKUP_UP"
    PICKUP_DOWN = "PICKUP_DOWN"
    DESTINATION = "DESTINATION"


class Request:
    def __init__(self, floor, type: RequestType) -> None:
        self.floor = floor
        self.type = type
    
    def get_floor(self):
        return self.floor

    def get_type(self):
        return self.type

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Request):
            return False
        return self.floor == other.floor and self.type == other.type

    def __hash__(self) -> int:
        return hash((self.floor, self.type))


class Elevator:
    MIN_FLOOR = 0
    MAX_FLOOR = 9

    def __init__(self, floor: int, direction: Direction, requests: list[Request] | None = None) -> None:
        self.current_floor = floor
        self.direction = direction
        self.requests: Set[Request] = set(requests or ())
        self.mis_dis = 3
    
    def add_request(self, request: Request) -> bool:
        if request.get_floor() < self.MIN_FLOOR or request.get_floor() > self.MAX_FLOOR:
            return False
        if request.get_floor() == self.current_floor:
            return True
        if request in self.requests:
            return False
        self.requests.add(request)
        return True

    def step(self):
        """
        core logic
        - If no requests move to idle state
        - If idle with requests, move to the nearest request 
        - If no requests to process, change direction (reverse)
        - check if should stop in floor request
        - sweep floors in the same direction

        edge:
        - No requests sit idle
        """

        if not self.requests:
            self.direction = Direction.IDLE
            return

        if self.direction == Direction.IDLE:
            # Find nearest request to establish initial direction (deterministic)
            nearest_rq = None
            min_distance = float('inf')
            
            for rq in self.requests:
                dd = abs(rq.get_floor() - self.current_floor)
                if dd < min_distance or (dd == min_distance and (nearest_rq is None or rq.get_floor() < nearest_rq.get_floor())):
                    min_distance = dd
                    nearest_rq = rq
            
            self.direction = Direction.UP if nearest_rq.get_floor() > self.current_floor else Direction.DOWN
        
        pickup_type = RequestType.PICKUP_UP if self.direction == Direction.UP else RequestType.PICKUP_DOWN
        pickup_request = Request(self.current_floor, pickup_type)
        destination_request = Request(self.current_floor, RequestType.DESTINATION)

        if pickup_request in self.requests or destination_request in self.requests:
            self.requests.discard(pickup_request)
            self.requests.discard(destination_request)
            if not self.requests:
                self.direction = Direction.IDLE
            return

        if not self.has_requests_ahead(self.direction):
            self.direction = Direction.DOWN if self.direction == Direction.UP else Direction.UP
            return

        if self.direction == Direction.UP:
            self.current_floor += 1
        elif self.direction == Direction.DOWN:
            self.current_floor -= 1

    def has_requests_ahead(self, dir):
        for request in self.requests:
            if dir == Direction.UP and request.get_floor() > self.current_floor:
                return True
            if dir == Direction.DOWN and request.get_floor() < self.current_floor:
                return True
        return False

    def has_requests_at_or_beyond(self, floor, dir):
        for request in self.requests:
            if dir == Direction.UP and request.get_floor() >= floor:
                if request.get_type() in (RequestType.PICKUP_UP, RequestType.DESTINATION):
                    return True
            if dir == Direction.DOWN and request.get_floor() <= floor:
                if request.get_type() in (RequestType.PICKUP_DOWN, RequestType.DESTINATION):
                    return True
        return False

    def get_floor(self):
        return self.current_floor

    def get_direction(self):
        return self.direction

    def get_current_floor(self):
        return self.current_floor
        

class ElevatorManager:
    MIN_FLOOR = 0
    MAX_FLOOR = 9
    
    def __init__(self, elevator: list[Elevator]) -> None:
        self.elevator: list[Elevator] = list(elevator)
        self.mis_dis = 3

    
    def step(self):
        for e in self.elevator:
            e.step()
    
    def find_nearest_moving_towards(self, request: Request) -> Elevator | None:
        floor = request.get_floor()
        direction = Direction.UP if request.get_type() == RequestType.PICKUP_UP else Direction.DOWN

        nearest = None
        min_distance = float('inf')

        for e in self.elevator:
            if e.get_direction() != direction:
                continue

            if (direction == Direction.UP and e.get_floor() > floor) or (direction == Direction.DOWN and e.get_floor() < floor):
                continue

            if not e.has_requests_at_or_beyond(floor, direction):
                continue

            distance = abs(e.get_floor() - floor)
            if distance > self.mis_dis:
                continue
            if distance < min_distance:
                min_distance = distance
                nearest = e

        return nearest
    
    def find_nearest_idle(self, request: Request) -> Elevator | None:
        floor = request.get_floor()
        nearest = None
        min_distance = float('inf')

        for e in self.elevator:
            if e.get_direction() != Direction.IDLE:
                continue

            distance = abs(e.get_floor() - floor)
            if distance < min_distance:
                min_distance = distance
                nearest = e

        return nearest

    def find_nearest(self, request: Request) -> Elevator | None:
        if not self.elevator:
            return None

        floor = request.get_floor()
        nearest = self.elevator[0]
        min_distance = abs(self.elevator[0].get_floor() - floor)

        for e in self.elevator:
            distance = abs(e.get_floor() - floor)
            if distance < min_distance:
                min_distance = distance
                nearest = e

        return nearest

    def _find_best_elevator(self, request: Request) -> Elevator | None:
        # can use different strategies for elevator selection
        # - find the nearest moving towards
        # - find the nearest idle
        # - find the nearest

        best = self.find_nearest_moving_towards(request)
        if best:
            return best

        best = self.find_nearest_idle(request)
        if best:
            return best

        return self.find_nearest(request)
        
        

    def request_elevator(self, floor, type: RequestType.PICKUP_DOWN | RequestType.PICKUP_UP) -> bool:
        """
        Core logic:
        - Find the best elevator
        - send request to elevator

        Edge case:
        found out of bounds
        """

        if floor < self.MIN_FLOOR or floor > self.MAX_FLOOR:
            return False

        if type == RequestType.DESTINATION:
            return False
        
        request = Request(floor=floor, type=type)
        res = self._find_best_elevator(request)
        if res is None:
            return False

        return res.add_request(request)
    



