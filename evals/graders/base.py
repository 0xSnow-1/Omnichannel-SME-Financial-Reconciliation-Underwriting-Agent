from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class GradingResult(BaseModel):
    grader_name: str
    grader_type: str  # "code", "model", "human"
    passed: bool
    score: float = Field(default=1.0, ge=0.0, le=1.0)
    details: str = ""
    cost_cents: float = Field(default=0.0, ge=0.0)


class BaseGrader(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the grader."""
        ...

    @property
    @abstractmethod
    def grader_type(self) -> str:
        """Type of grader: 'code', 'model', or 'human'."""
        ...

    @abstractmethod
    def grade(self, state: dict[str, Any], ground_truth: dict[str, Any]) -> GradingResult:
        """Grade the agent execution state against ground truth."""
        ...
