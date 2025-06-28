# Design a hash map

# Constraints and assumptions
# For simplicity, are the keys integers only?
# Yes
# For collision resolution, can we use chaining?
# Yes
# Do we have to worry about load factors?
# No
# Can we assume inputs are valid or do we have to validate them?
# Assume they're valid
# Can we assume this fits memory?
# Yes

class Item(object):
    def __init__(self, key: int, value: any) -> None:
        self.key = key
        self.value = value


class HashMap(object):
    def __init__(self, size: int = 100) -> None:
        self.size = size
        self.store: list[list[Item]] = [[] for _ in range(0, size)]

    def _hash(self, key: int) -> int:
        return key % self.size
    
    def set_item(self, key: int, value: any) -> None:
        hash_key = self._hash(key)
        hash_key_chain = self.store[hash_key]
        for i,it in enumerate(hash_key_chain):
            if it.key == key:
                hash_key_chain[i] = Item(key=key, value=value)
                return
        hash_key_chain.append(Item(key=key, value=value))
        self.store[hash_key] = hash_key_chain

    def get_item(self, key: int) -> any:
        hash_key = self._hash(key)
        hash_key_chain = self.store[hash_key]
        value = None
        for it in hash_key_chain:
            if it.key == key:
                value = it.value
                return value
        if not value:
            raise KeyError()
        
    def remove_item(self, key: int) -> None:
        hash_key = self._hash(key)
        hash_key_chain = self.store[hash_key]
        for i, it in enumerate(hash_key_chain):
            if it.key == key:
                del hash_key_chain[i]
                return 
        raise KeyError()



map = HashMap()
map.set_item(key=1, value="Sounak")
map.set_item(key=2, value="Gupta")
ss = map.get_item(key=1)
st = map.get_item(key=2)
print(ss,st)
map.remove_item(2)
st = map.get_item(key=2)
print(ss)