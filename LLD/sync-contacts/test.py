"""
Sync Contacts - Interview Notes
===============================

Problem in simple words
-----------------------
We need two APIs:

1. sync_contacts(user_id, contacts)
   Save the user's latest phone book. Every sync REPLACES the old phone book.

2. prospective_users(user_id)
   Return the user's contacts who are NOT on Ziina yet, along with how many
   other Ziina users also know that phone number.

There is one external API:
    is_ziina_user(phone_number) -> bool

Clarifying questions I should ask first
---------------------------------------
1. Should "friends_on_ziina" count the current user?
   I implemented it as NO, because a user should not count as their own friend.

2. How big is the data?
   Number of users, average contacts per user, and total unique phone numbers.
   This decides whether in-memory is okay or we need DB/Redis.

3. Is there a bulk API?
   is_ziina_user(phone) is slower if called once per contact. A bulk API like
   is_ziina_users(list_of_phones) would be better.

4. How fresh should the Ziina-user check be?
   This code uses an LRU cache. In production I would add TTL or invalidate the
   cache when a phone number joins Ziina.

5. Will this run on one server or many servers?
   This in-memory solution works for one process. For many servers, the data
   must move to shared storage like Postgres/Redis.

Design I am using
-----------------
Main idea: keep two indexes.

1. user -> phones
   Example: "alice" -> {"111", "222"}
   This lets me quickly get one user's contacts.

2. phone -> users
   Example: "111" -> {"alice", "bob"}
   This lets me quickly count how many Ziina users know a phone number.

Why this is better:
    Without phone -> users, I would scan every user's contacts each time.
    With phone -> users, friends_on_ziina is just len(phone_to_users[phone]).

Code structure
--------------
ContactRepo:
    Owns the two indexes and keeps them consistent.

ContactService:
    Handles the use case: normalize phones, sync contacts, and build the
    prospective user response.

ZiinaDirectory:
    Protocol for the external is_ziina_user API. Easy to mock in tests.

CachingZiinaDirectory:
    Wraps the external API with lru_cache so repeated phone checks are cheap.

How sync works
--------------
When a user syncs, I compare old contacts vs new contacts:

    removed = old_contacts - new_contacts
    added   = new_contacts - old_contacts

Then I update only the changed phones in the reverse index. If the same list is
synced again, almost nothing changes.

Thread safety explanation
-------------------------
The repo uses RLock because sync updates two data structures. The lock prevents
another thread from seeing half-updated data.

The cache does NOT use my own lock because functools.lru_cache is already
thread-safe. Adding one big lock around every cache lookup would slow down all
reads. The only small trade-off is that two threads may both call the backend
for the same new phone at the same time, which is acceptable here.

prospective_users reads in small steps, so it is eventually consistent. If the
interviewer asks for a strict snapshot, I would either:
    1. read contacts and counts under one repo lock, or
    2. use copy-on-write snapshots.

Asyncio / queue discussion
--------------------------
Asyncio is useful for is_ziina_user because that is network I/O.
If one user has 500 contacts and we call the API one by one, latency is bad.
Better options:
    1. Best: use a bulk API.
    2. If no bulk API: make the directory async and use asyncio.gather.

A thread-safe queue is useful if writes become heavy:
    - Put sync requests into queue.Queue.
    - One writer thread consumes them and updates the indexes in order.
    - Readers can be made simpler because only one thread mutates the index.

For this interview version, RLock is enough.

Complexity
----------
Let:
    C = contacts of one user
    D = changed contacts during sync
    K = prospective users returned
    E = total saved contact edges across all users

sync_contacts:
    Time  = O(D) after comparing sets. First sync is O(C).
    Space = O(C) for that user's stored contacts.

prospective_users:
    Time  = O(C + K log K). We scan the user's contacts and sort the result.
    Space = O(K) for the result.

Overall storage:
    O(E), stored in two maps: user -> phones and phone -> users.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from threading import RLock
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Set
import unittest


@dataclass(frozen=True)
class ProspectiveUser:
    phone_number: str
    friends_on_ziina: int


class ZiinaDirectory(Protocol):
    def is_ziina_user(self, phone_number: str) -> bool: ...


class CacheZiinaDirectory:
    def __init__(self, inner: ZiinaDirectory, *, maxsize: int = 128) -> None:
        self._inner = inner

        @lru_cache(maxsize=maxsize)
        def _lookup(phone_number: str) -> bool:
            return self._inner.is_ziina_user(phone_number)

        self._lookup = _lookup

    def is_ziina_user(self, phone_number: str) -> bool:
        return self._lookup(phone_number)

    def cache_clear(self) -> None:
        self._lookup.cache_clear()

    def cache_info(self):
        return self._lookup.cache_info()


class ContactRepo:
    """In-memory storage with forward + reverse indexes."""

    def __init__(self) -> None:
        # no implicit bucket creation
        self._users_to_phone: Dict[str, Set[str]] = {}
        # implicit bucket creation is needed so defaultdict
        self._phone_to_users: Dict[str, Set[str]] = defaultdict(set)
        self._lock = RLock()

    def replace(self, user_id: str, new_contacts: Set[str]) -> None:
        """Replace user contacts atomically using a delta update."""
        with self._lock:
            old_contacts = self._users_to_phone.get(user_id, set())
            removed = old_contacts - new_contacts
            added = new_contacts - old_contacts

            for phone in removed:
                owners = self._phone_to_users.get(phone)
                if owners is None:
                    continue
                owners.discard(user_id)
                if not owners:
                    del self._phone_to_users[phone]

            for phone in added:
                self._phone_to_users[phone].add(user_id)

            self._users_to_phone[user_id] = set(new_contacts)

    def get_contacts(self, user_id: str) -> Set[str]:
        with self._lock:
            return set(self._users_to_phone.get(user_id, ()))

    def get_friends_on_ziina(self, phone: str, exclude_user_id: Optional[str] = None) -> int:
        """Count users who have this phone in their contacts.

        ``exclude_user_id`` drops the requester so they don't count themselves
        as one of "their friends on Ziina".
        """
        with self._lock:
            owners = self._phone_to_users.get(phone, set())
            if exclude_user_id is not None:
                owners = owners - {exclude_user_id}
            return len(owners)


class ContactService:
    @staticmethod
    def default_normaliser(phone: str) -> str:
        return phone.strip().replace(" ", "").replace("-", "")

    def __init__(
        self,
        contact_repo: ContactRepo,
        directory: ZiinaDirectory,
        normaliser: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._contact_repo = contact_repo
        self._directory = directory
        self._normaliser = normaliser or self.default_normaliser

    def sync_contacts(self, user_id: str, contacts: Iterable[str]) -> None:
        if not user_id:
            raise ValueError("Invalid user id")

        normalized_contacts: Set[str] = set()
        for phone in contacts:
            if phone is None:
                continue
            normalized = self._normaliser(phone)
            if normalized:
                normalized_contacts.add(normalized)

        self._contact_repo.replace(user_id=user_id, new_contacts=normalized_contacts)

    def prospective_users(self, user_id: str) -> List[ProspectiveUser]:
        if not user_id:
            raise ValueError("Invalid user id")

        # Consistency note: each repo/directory call below takes the lock
        # independently, so this method gives a per-call (eventually consistent)
        # view, not a single atomic snapshot. A concurrent replace() mid-loop
        # could yield a count that never existed at one instant. Acceptable for
        # a read-mostly invite feature; for a strict snapshot we'd read the
        # contacts + counts under one lock, or use a copy-on-write reference swap.
        contacts = self._contact_repo.get_contacts(user_id=user_id)
        result: List[ProspectiveUser] = []

        for phone in contacts:
            if self._directory.is_ziina_user(phone):
                continue
            result.append(
                ProspectiveUser(
                    phone_number=phone,
                    friends_on_ziina=self._contact_repo.get_friends_on_ziina(
                        phone, exclude_user_id=user_id
                    ),
                )
            )

        result.sort(key=lambda item: item.phone_number)
        return result


class FakeServerDirectory:
    def __init__(self, phones: Set[str]) -> None:
        self.phones = set(phones)
        self.call_count = 0

    def is_ziina_user(self, phone_number: str) -> bool:
        self.call_count += 1
        return phone_number in self.phones


def build_demo_service() -> ContactService:
    """Basic data setup to run and show output quickly."""
    fake_dir = FakeServerDirectory({"81621927", "729797221", "923799273"})
    cache_dir = CacheZiinaDirectory(inner=fake_dir)
    repo = ContactRepo()
    service = ContactService(contact_repo=repo, directory=cache_dir)

    service.sync_contacts("alice", ["8162-1927", "5555-1111", "6666-2222"])
    service.sync_contacts("bob", ["5555-1111", "7297-972-21"])
    return service


class ContactServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = FakeServerDirectory({"100", "200"})
        self.service = ContactService(ContactRepo(), CacheZiinaDirectory(directory))

    def test_sync_replace_add_remove(self) -> None:
        self.service.sync_contacts("u1", ["100", "300", "400"])
        self.service.sync_contacts("u1", ["100", "500"])

        # 300/400 removed, 500 added. Count excludes u1 itself -> 0.
        result = self.service.prospective_users("u1")
        self.assertEqual(
            result,
            [ProspectiveUser(phone_number="500", friends_on_ziina=0)],
        )

    def test_prospective_users_excludes_ziina_numbers(self) -> None:
        self.service.sync_contacts("u1", ["100", "300"])
        result = self.service.prospective_users("u1")
        # Only u1 has 300, and the requester is excluded -> 0.
        self.assertEqual(
            result,
            [ProspectiveUser(phone_number="300", friends_on_ziina=0)],
        )

    def test_friends_on_ziina_count_across_users(self) -> None:
        self.service.sync_contacts("u1", ["300"])
        self.service.sync_contacts("u2", ["300"])
        result = self.service.prospective_users("u1")
        # u1 and u2 both have 300; excluding the requester u1 leaves only u2 -> 1.
        self.assertEqual(
            result,
            [ProspectiveUser(phone_number="300", friends_on_ziina=1)],
        )


if __name__ == "__main__":
    demo_service = build_demo_service()
    print("Prospective for alice:", demo_service.prospective_users("alice"))
    print("Prospective for bob:", demo_service.prospective_users("bob"))
    print("\nRunning tests...\n")
    unittest.main(argv=["ignored", "-v"], exit=False)
