from typing import Any

from sme_copilot.interfaces.contracts import LLMProvider
from sme_copilot.services.llm_provider import get_llm_provider

from evals.graders.base import BaseGrader, GradingResult


class LLMJudgeGrader(BaseGrader):
    """Model-based LLM Judge Grader.

    Evaluates qualitative underwriting risk summaries against extracted financial facts.
    SAFETY NOTE: Execution is DISABLED by default (enabled=False) to avoid incurring
    unexpected LLM API costs. Live execution only runs when explicitly activated.
    """

    def __init__(
        self,
        enabled: bool = False,
        provider: LLMProvider | None = None,
    ) -> None:
        self.enabled = enabled
        self._provider = provider

    @property
    def name(self) -> str:
        return "llm_qualitative_judge"

    @property
    def grader_type(self) -> str:
        return "model"

    def grade(self, state: dict[str, Any], ground_truth: dict[str, Any]) -> GradingResult:
        # Zero-cost guard: do NOT make live LLM calls unless explicitly enabled by user
        if not self.enabled:
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=True,
                score=1.0,
                details=(
                    "[DRY-RUN / SKIPPED] LLM Judge execution disabled (zero cost). "
                    "Pass --enable-llm-judge to execute live judge."
                ),
                cost_cents=0.0,
            )

        provider = self._provider or get_llm_provider()
        review_state = state.get("review_state")
        notes = getattr(review_state, "reviewer_notes", "") or "No notes provided"
        true_revenue = ground_truth.get("true_revenue", 0.0)

        prompt = (
            "You are an expert Credit Committee Auditor. Grade the summary:\n\n"
            f"Underwriter Notes: {notes}\n"
            f"Ground Truth True Revenue: ₱{true_revenue:,.2f}\n\n"
            "Rubric:\n"
            "1. Factual consistency: Does not claim revenue contradicting true revenue.\n"
            "2. Tone: Defensible to a credit committee.\n"
            "Reply with PASS or FAIL followed by a 1-sentence rationale."
        )

        try:
            response = provider.summarize(prompt)
            passed = "pass" in response.lower()
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=passed,
                score=1.0 if passed else 0.5,
                details=f"LLM Judge Evaluation: {response[:150]}",
                cost_cents=0.15,  # Estimated Haiku token cost
            )
        except Exception as exc:
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=False,
                score=0.0,
                details=f"LLM Judge invocation failed: {exc}",
                cost_cents=0.0,
            )
