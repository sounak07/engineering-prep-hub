"""
Resource Manager
================

Repository : ResourceStore        — owns the id->Resource map + per-type free pools
State      : ResourceState        — AVAILABLE / ALLOCATED, drives what operations are legal
Strategy   : AllocationStrategy   — which free resource to hand out (FIFO / LIFO / pluggable)
Facade     : ResourceManager      — the interview-facing API

Free pool representation: OrderedDict[resource_id -> None] per type, NOT a deque.
Why: a deque gives you O(1) pop-from-either-end, but O(n) removal of an ARBITRARY
element (needed when you remove_resource() something sitting in the middle of the
free pool). OrderedDict is a dict underneath, so deleting any key is O(1), while
still preserving insertion order for FIFO/LIFO popping. Same trick as an
LRU-cache / "ordered set" -- one structure, two jobs.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from enum import Enum
from typing import Dict, Optional


class ResourceState(Enum):
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"


class Resource:
    __slots__ = ("resource_id", "resource_type", "state")

    def __init__(self, resource_id: str, resource_type: str):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.state = ResourceState.AVAILABLE

    def __repr__(self):
        return f"Resource({self.resource_id}, {self.resource_type}, {self.state.value})"


# ---------------- Strategy: which free resource to hand out ----------------

class AllocationStrategy(ABC):
    @abstractmethod
    def pick(self, free_pool: "OrderedDict[str, None]") -> Optional[str]:
        """Remove and return one resource_id from the pool, or None if empty."""
        ...

    def on_release(self, free_pool: "OrderedDict[str, None]", resource_id: str) -> None:
        """Default: released resources rejoin the pool at the end."""
        free_pool[resource_id] = None


class FIFOAllocationStrategy(AllocationStrategy):
    """Hand out the resource that's been sitting free the longest."""

    def pick(self, free_pool):
        if not free_pool:
            return None
        resource_id, _ = free_pool.popitem(last=False)  # oldest entry
        return resource_id


class LIFOAllocationStrategy(AllocationStrategy):
    """Hand out the most recently freed resource (e.g. cache-warm connections)."""

    def pick(self, free_pool):
        if not free_pool:
            return None
        resource_id, _ = free_pool.popitem(last=True)   # newest entry
        return resource_id


# ---------------- Repository ----------------

class ResourceStore:
    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._free_pools: Dict[str, "OrderedDict[str, None]"] = defaultdict(OrderedDict)

    def add(self, resource_id: str, resource_type: str) -> Resource:
        if resource_id in self._resources:
            raise ValueError(f"Resource already exists: {resource_id}")
        resource = Resource(resource_id, resource_type)
        self._resources[resource_id] = resource
        self._free_pools[resource_type][resource_id] = None
        return resource

    def get(self, resource_id: str) -> Optional[Resource]:
        return self._resources.get(resource_id)

    def delete(self, resource_id: str) -> None:
        resource = self._resources.pop(resource_id)  # KeyError if missing -- caller's job to check first
        pool = self._free_pools.get(resource.resource_type)
        if pool is not None:
            pool.pop(resource_id, None)  # O(1) -- this is the whole point of OrderedDict here

    def free_pool(self, resource_type: str) -> "OrderedDict[str, None]":
        return self._free_pools[resource_type]

    def available_count(self, resource_type: str) -> int:
        return len(self._free_pools.get(resource_type, ()))


# ---------------- Facade ----------------

class ResourceManager:
    def __init__(self, strategy: Optional[AllocationStrategy] = None):
        self._store = ResourceStore()
        self._strategy = strategy or FIFOAllocationStrategy()
        self._allocations: Dict[str, str] = {}   # resource_id -> consumer_id

    def add_resource(self, resource_id: str, resource_type: str) -> None:
        self._store.add(resource_id, resource_type)

    def remove_resource(self, resource_id: str) -> None:
        resource = self._store.get(resource_id)
        if resource is None:
            raise KeyError(f"No such resource: {resource_id}")
        if resource.state == ResourceState.ALLOCATED:
            raise ValueError(f"Cannot remove {resource_id}: currently allocated, release it first")
        self._store.delete(resource_id)

    def allocate(self, resource_type: str, consumer_id: str) -> Optional[str]:
        pool = self._store.free_pool(resource_type)
        resource_id = self._strategy.pick(pool)
        if resource_id is None:
            return None
        resource = self._store.get(resource_id)
        resource.state = ResourceState.ALLOCATED
        self._allocations[resource_id] = consumer_id
        return resource_id

    def release(self, resource_id: str) -> None:
        resource = self._store.get(resource_id)
        if resource is None:
            raise KeyError(f"No such resource: {resource_id}")
        if resource.state != ResourceState.ALLOCATED:
            raise ValueError(f"Resource {resource_id} is not currently allocated")
        resource.state = ResourceState.AVAILABLE
        del self._allocations[resource_id]
        pool = self._store.free_pool(resource.resource_type)
        self._strategy.on_release(pool, resource_id)

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        return self._store.get(resource_id)   # read-only query -> None sentinel, not an exception

    def available_count(self, resource_type: str) -> int:
        return self._store.available_count(resource_type)


# ---------------- sanity checks ----------------
if __name__ == "__main__":
    rm = ResourceManager()  # defaults to FIFO

    rm.add_resource("r1", "gpu")
    rm.add_resource("r2", "gpu")
    rm.add_resource("r3", "gpu")
    assert rm.available_count("gpu") == 3

    # FIFO: r1 was added first, should be allocated first
    got = rm.allocate("gpu", "consumer-A")
    assert got == "r1"
    assert rm.available_count("gpu") == 2
    assert rm.get_resource("r1").state == ResourceState.ALLOCATED

    got2 = rm.allocate("gpu", "consumer-B")
    assert got2 == "r2"

    # pool exhausted except r3
    assert rm.available_count("gpu") == 1
    got3 = rm.allocate("gpu", "consumer-C")
    assert got3 == "r3"

    # pool now empty
    assert rm.allocate("gpu", "consumer-D") is None

    # release r2, it should be allocatable again
    rm.release("r2")
    assert rm.available_count("gpu") == 1
    got4 = rm.allocate("gpu", "consumer-E")
    assert got4 == "r2"

    # can't remove an allocated resource
    try:
        rm.remove_resource("r1")
        assert False
    except ValueError:
        pass

    # release then remove works, and O(1) removal from the middle of a pool
    rm.add_resource("r4", "gpu")
    rm.add_resource("r5", "gpu")
    # free pool order right now: [r4, r5] (r1/r2/r3 all allocated)
    rm.remove_resource("r4")   # removing from the middle/front of the free pool
    assert rm.available_count("gpu") == 1
    assert rm.get_resource("r4") is None

    # double release should fail
    rm.release("r3")
    try:
        rm.release("r3")
        assert False
    except ValueError:
        pass

    # querying a resource that was never added -> None, not an exception
    assert rm.get_resource("does-not-exist") is None

    # LIFO strategy behaves differently
    lifo_rm = ResourceManager(strategy=LIFOAllocationStrategy())
    lifo_rm.add_resource("x1", "cpu")
    lifo_rm.add_resource("x2", "cpu")
    lifo_rm.add_resource("x3", "cpu")
    assert lifo_rm.allocate("cpu", "c1") == "x3"   # most recently added, LIFO
    assert lifo_rm.allocate("cpu", "c2") == "x2"

    print("ALL PASSED")