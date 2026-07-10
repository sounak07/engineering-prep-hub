from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Protocol
from pydantic import BaseModel, Field, field_validator
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class ProspectiveUser:
    phone_no: str
    friends_on_ziina: int


class SyncContacts(BaseModel):
    user_id: str = Field(min_length=1)
    new_contacts: list[str] = Field(min_length=1)

    @field_validator("user_id")
    @classmethod
    def valid_user_id(cls, user_id: str):
        value = user_id.strip()
        if not value:
            raise ValueError("Invalid user id")
        return value

    @field_validator("new_contacts")
    @classmethod
    def valid_contacts(cls, contacts: list[str]):
        if len(contacts) == 0:
            raise ValueError("Error: no contacts")
        
        for phone in contacts:
            if len(phone) < 7:
                raise ValueError(f"Invalid phone {phone}")
        return contacts


class ZiinaDirectory(ABC):
    @abstractmethod
    def is_ziina_user(self, phone: str) -> bool:
        pass



class CacheDirectory(ZiinaDirectory):
    def __init__(self, inner: ZiinaDirectory, * ,max_size=128) -> None:
        self._inner = inner

        @lru_cache(maxsize=max_size)
        def lookup(phone: str):
            return self._inner.is_ziina_user(phone)

        self._lookup = lookup

    def is_ziina_user(self, phone: str) -> bool:
        return self._lookup(phone)

    def clear(self)->None:
        return self._lookup.cache_clear()


class ContactRepo:
    def __init__(self) -> None:
        self._user_phones: dict[str, set[str]] = {}
        self._phone_users: dict[str, set[str]] = defaultdict(set)


    def replace(self, user_id: str, new_contacts: set[str]) -> None:
        old_contacts = self._user_phones.get(user_id, set())

        to_add = new_contacts - old_contacts
        to_remove = old_contacts - new_contacts


        for phone in to_remove:
            owners = self._phone_users.get(phone)
            if owners is None:
                continue
            owners.discard(user_id)
            if not owners:
                del self._phone_users[phone]
            
        for phone in to_add:
            self._phone_users[phone].add(user_id)

        self._user_phones[user_id] = set(new_contacts)

    def get_contacts(self, user_id: str) -> set[str]:
        return set(self._user_phones.get(user_id, set()))

    def friends_in_ziina(self, phone: str, exclude_user: str) -> int:
        owners = self._phone_users.get(phone)
        if owners:
            owners = owners - {exclude_user}
            return len(owners)
        return 0


class ContactsService:
    @staticmethod
    def default_normaliser(phone: str) -> str:
        return phone.strip().replace("-","").replace(" ", "")

    def __init__(self, ziina_dir: ZiinaDirectory, normaliser: Callable[[str], str] | None = None) -> None:
        self._ziina_dir = ziina_dir
        self._contact_repo = ContactRepo()
        self._normaliser = normaliser or self.default_normaliser

    
    def sync_contacts(self, sync_data: SyncContacts) -> None:
        norm_contacts: set[str] = set()

        for phone in sync_data.new_contacts:
            if not phone:
                continue
            norm = self._normaliser(phone)
            if not norm:
                continue
            norm_contacts.add(norm)
        
        self._contact_repo.replace(sync_data.user_id, new_contacts=norm_contacts)

    
    def prospective_users(self, user_id: str) -> list[ProspectiveUser]:
        contacts = self._contact_repo.get_contacts(user_id=user_id)

        res: list[ProspectiveUser] = []

        for phone in contacts:
            if self._ziina_dir.is_ziina_user(phone):
                continue
            res.append(
                ProspectiveUser(
                    phone_no=phone,
                    friends_on_ziina=self._contact_repo.friends_in_ziina(phone=phone, exclude_user=user_id)
                )
            )
        return res

class FakeServerDirectory(ZiinaDirectory):
    def __init__(self, phones: set[str]) -> None:
        self.phones = set(phones)

    def is_ziina_user(self, phone_number: str) -> bool:
        return phone_number in self.phones

def build_demo_service() -> ContactsService:
    """Basic data setup to run and show output quickly."""
    fake_dir = FakeServerDirectory({"81621927", "729797221", "923799273"})
    cache_dir = CacheDirectory(inner=fake_dir)
    service = ContactsService(ziina_dir=cache_dir)

    service.sync_contacts(SyncContacts(
        user_id="Sounak",
        new_contacts=["8162-1927", "5555-1111", "6666-2222"]
    ))
    service.sync_contacts(SyncContacts(
        user_id="Yuri",
        new_contacts=["5555-1111", "7297-972-21"]
    ))
    return service

def demo():
    svc = build_demo_service()
    print(svc.prospective_users("Yuri"))

demo()