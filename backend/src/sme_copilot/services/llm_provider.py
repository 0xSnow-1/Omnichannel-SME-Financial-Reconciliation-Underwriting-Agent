import os
from typing import TypeVar

from pydantic import BaseModel

from sme_copilot.interfaces.contracts import LLMProvider

T = TypeVar("T", bound=BaseModel)


class StubLLMProvider(LLMProvider):
    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        return schema()

    def summarize(self, text: str) -> str:
        return "Stub summary."


def get_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "stub")
    if provider_name == "stub":
        return StubLLMProvider()
    # Bedrock Haiku implementation deferred to Phase 1
    return StubLLMProvider()
