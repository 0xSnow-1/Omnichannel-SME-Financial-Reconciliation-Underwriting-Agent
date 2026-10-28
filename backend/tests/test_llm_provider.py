from sme_copilot.services.llm_provider import StubLLMProvider, get_llm_provider


def test_stub_extract():
    provider = StubLLMProvider()
    from pydantic import BaseModel

    class Dummy(BaseModel):
        value: str = "default"

    result = provider.extract_structured("prompt", Dummy)
    assert isinstance(result, Dummy)


def test_stub_summarize():
    provider = StubLLMProvider()
    assert provider.summarize("text") == "Stub summary."


def test_get_llm_provider():
    provider = get_llm_provider()
    assert provider is not None
