from dataclasses import dataclass

ACTIVE = "ACTIVE"

@dataclass(frozen=True)
class Member:
    id: str
    status: str

    def is_active(self) -> bool:
        return self.status == ACTIVE

@dataclass(frozen=True)
class Book:
    id: int
    available: int

    def is_available(self) -> bool:
        return self.available > 0
