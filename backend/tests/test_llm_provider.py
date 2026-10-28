from unittest.mock import MagicMock, patch

from pydantic import BaseModel
from sme_copilot.services.llm_provider import (
    BedrockLLMProvider,
    OpenAILLMProvider,
    StubLLMProvider,
    get_llm_provider,
)


class DummySchema(BaseModel):
    name: str = "Test"
    amount: float = 100.0


def test_stub_extract():
    provider = StubLLMProvider()
    result = provider.extract_structured("prompt", DummySchema)
    assert isinstance(result, DummySchema)


def test_stub_summarize():
    provider = StubLLMProvider()
    assert "cash inflows" in provider.summarize("financial text")


def test_get_llm_provider_variants(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    assert isinstance(get_llm_provider(), StubLLMProvider)

    monkeypatch.setenv("LLM_PROVIDER", "bedrock-haiku")
    assert isinstance(get_llm_provider(), BedrockLLMProvider)

    monkeypatch.setenv("LLM_PROVIDER", "openai-gpt4o")
    assert isinstance(get_llm_provider(), OpenAILLMProvider)


def test_bedrock_provider_fallback_on_error():
    provider = BedrockLLMProvider()
    # When no real AWS connection, extract_structured safely falls back to Stub
    result = provider.extract_structured("prompt", DummySchema)
    assert isinstance(result, DummySchema)

    summary = provider.summarize("prompt")
    assert isinstance(summary, str)


def test_openai_provider_fallback_on_error():
    provider = OpenAILLMProvider()
    result = provider.extract_structured("prompt", DummySchema)
    assert isinstance(result, DummySchema)

    summary = provider.summarize("prompt")
    assert isinstance(summary, str)


def test_bedrock_mock_invoke():
    provider = BedrockLLMProvider()
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = DummySchema(
        name="Extracted", amount=500.0
    )

    with patch("langchain_aws.ChatBedrockConverse", return_value=mock_llm):
        res = provider.extract_structured("Extract data", DummySchema)
        assert res.name == "Extracted"
        assert res.amount == 500.0
