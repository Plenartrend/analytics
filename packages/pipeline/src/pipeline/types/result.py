from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class Result(ABC, Generic[K, V]):
    def __init__(self, value: K | V):
        self.value = value

    @abstractmethod
    def unwrap(self) -> K | V:
        raise NotImplementedError("Subclasses must implement this method")

    def is_ok(self) -> bool:
        return isinstance(self, Ok)

    def is_err(self) -> bool:
        return not self.is_ok()


class Ok(Result):
    def __init__(self, value: K):
        super().__init__(value)

    def unwrap(self) -> K:
        return self.value


class Err(Result):
    def __init__(self, value: V):
        super().__init__(value)

    def unwrap(self) -> V:
        return self.value
