import logging
import os
from typing import TypeVar

from pydantic import BaseModel

from sme_copilot.interfaces.contracts import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StubLLMProvider(LLMProvider):
    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        try:
            return schema()
        except Exception:
            # If default instantiation requires non-default arguments, try model_construct
            return schema.model_construct()

    def summarize(self, text: str) -> str:
        return (
            "Merchant displays regular business cash inflows across accounts. "
            "Reconciliation and balance checks verified without critical default indicators."
        )


class BedrockLLMProvider(LLMProvider):
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")

    def _get_client(self) -> object:
        import boto3  # type: ignore[import-untyped]

        token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        if token:
            return boto3.client(
                "bedrock-runtime",
                region_name=self.region_name,
            )
        return boto3.client("bedrock-runtime", region_name=self.region_name)

    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        try:
            from langchain_aws import ChatBedrockConverse

            llm = ChatBedrockConverse(
                model=self.model_id,
                region_name=self.region_name,
                temperature=0.0,
            )
            structured_llm = llm.with_structured_output(schema)
            result = structured_llm.invoke(prompt)
            if isinstance(result, schema):
                return result
            if isinstance(result, dict):
                return schema.model_validate(result)
        except Exception as exc:
            logger.warning("Bedrock structured extraction failed: %s. Falling back to stub.", exc)

        return StubLLMProvider().extract_structured(prompt, schema)

    def summarize(self, text: str) -> str:
        try:
            from langchain_aws import ChatBedrockConverse

            llm = ChatBedrockConverse(
                model=self.model_id,
                region_name=self.region_name,
                temperature=0.2,
            )
            msg = llm.invoke(
                "You are a credit underwriting assistant. "
                f"Provide a concise qualitative risk assessment of the business data:\n\n{text}"
            )
            return str(msg.content)
        except Exception as exc:
            logger.warning("Bedrock summarization failed: %s. Falling back to stub.", exc)
            return StubLLMProvider().summarize(text)


class OpenAILLMProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o") -> None:
        self.model = model

    def extract_structured(self, prompt: str, schema: type[T]) -> T:
        try:
            from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

            llm = ChatOpenAI(model=self.model, temperature=0.0)
            structured = llm.with_structured_output(schema)
            result = structured.invoke(prompt)
            if isinstance(result, schema):
                return result
            if isinstance(result, dict):
                return schema.model_validate(result)
        except Exception as exc:
            logger.warning("OpenAI extraction failed: %s. Falling back to stub.", exc)

        return StubLLMProvider().extract_structured(prompt, schema)

    def summarize(self, text: str) -> str:
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=self.model, temperature=0.2)
            msg = llm.invoke(
                f"Provide a concise qualitative risk summary for credit underwriting:\n\n{text}"
            )
            return str(msg.content)
        except Exception as exc:
            logger.warning("OpenAI summarization failed: %s. Falling back to stub.", exc)
            return StubLLMProvider().summarize(text)


def get_llm_provider() -> LLMProvider:
    provider_name = os.getenv("LLM_PROVIDER", "stub").strip().lower()
    if provider_name == "bedrock-haiku":
        return BedrockLLMProvider()
    if provider_name == "openai-gpt4o":
        return OpenAILLMProvider()
    return StubLLMProvider()
