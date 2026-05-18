from __future__ import annotations

from abc import ABC, abstractmethod


class BaseFieldExtractor(ABC):
    field_key: str

    @abstractmethod
    def extract(self, context: dict) -> list[dict]:
        raise NotImplementedError
