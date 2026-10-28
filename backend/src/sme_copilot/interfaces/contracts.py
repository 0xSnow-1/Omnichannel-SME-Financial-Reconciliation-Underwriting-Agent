from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    @abstractmethod
    def extract_structured(self, prompt: str, schema: type[T]) -> T: ...

    @abstractmethod
    def summarize(self, text: str) -> str: ...


class Connector(ABC):
    @abstractmethod
    def fetch_documents(self, source_id: str) -> list[Any]: ...

    @abstractmethod
    def validate_source(self, source_id: str) -> bool: ...
