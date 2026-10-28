from typing import Any

from sme_copilot.schemas.models import ExtractedDocument

from evals.graders.base import BaseGrader, GradingResult


class SchemaComplianceGrader(BaseGrader):
    @property
    def name(self) -> str:
        return "schema_compliance"

    @property
    def grader_type(self) -> str:
        return "code"

    def grade(self, state: dict[str, Any], ground_truth: dict[str, Any]) -> GradingResult:
        docs = state.get("extracted_documents", [])
        if not docs:
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=False,
                score=0.0,
                details="No extracted documents found in state",
            )

        for d in docs:
            if not isinstance(d, ExtractedDocument):
                return GradingResult(
                    grader_name=self.name,
                    grader_type=self.grader_type,
                    passed=False,
                    score=0.0,
                    details=f"Document {type(d)} does not conform to ExtractedDocument schema",
                )
            if not d.application_id or not d.file_ref:
                return GradingResult(
                    grader_name=self.name,
                    grader_type=self.grader_type,
                    passed=False,
                    score=0.5,
                    details="Extracted document missing mandatory application_id or file_ref",
                )

        return GradingResult(
            grader_name=self.name,
            grader_type=self.grader_type,
            passed=True,
            score=1.0,
            details=f"All {len(docs)} documents conform to strict Pydantic V2 schemas",
        )


class NumericAccuracyGrader(BaseGrader):
    @property
    def name(self) -> str:
        return "numeric_accuracy"

    @property
    def grader_type(self) -> str:
        return "code"

    def grade(self, state: dict[str, Any], ground_truth: dict[str, Any]) -> GradingResult:
        docs = state.get("extracted_documents", [])
        bank_doc = next(
            (d for d in docs if "bank" in getattr(d.file_ref, "filename", "").lower()), None
        )

        expected_count = ground_truth.get("total_bank_transactions", 0)
        actual_count = len(bank_doc.transactions) if bank_doc else 0

        if expected_count == 0:
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=True,
                score=1.0,
                details="No expected transactions in ground truth",
            )

        accuracy_score = min(actual_count / expected_count, 1.0)
        passed = accuracy_score >= 0.85

        return GradingResult(
            grader_name=self.name,
            grader_type=self.grader_type,
            passed=passed,
            score=round(accuracy_score, 3),
            details=f"Extracted {actual_count}/{expected_count} txns ({accuracy_score:.1%})",
        )


class ArithmeticIntegrityGrader(BaseGrader):
    @property
    def name(self) -> str:
        return "arithmetic_integrity"

    @property
    def grader_type(self) -> str:
        return "code"

    def grade(self, state: dict[str, Any], ground_truth: dict[str, Any]) -> GradingResult:
        val_results = state.get("validation_results", [])
        has_planted_mismatch = ground_truth.get("has_arithmetic_mismatch", False)

        has_validation_failure = any(not vr.passed for vr in val_results)

        if has_planted_mismatch:
            # Grader passes if the system correctly caught the arithmetic tampering
            caught = has_validation_failure
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=caught,
                score=1.0 if caught else 0.0,
                details=(
                    "Correctly caught planted arithmetic mismatch"
                    if caught
                    else "FAILED to catch planted arithmetic mismatch"
                ),
            )
        else:
            # Clean case: should pass without errors
            passed = not has_validation_failure
            details = "Clean arithmetic verified" if passed else "False positive error"
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=passed,
                score=1.0 if passed else 0.0,
                details=details,
            )


class SourcePointerGrader(BaseGrader):
    @property
    def name(self) -> str:
        return "source_pointer_validity"

    @property
    def grader_type(self) -> str:
        return "code"

    def grade(self, state: dict[str, Any], ground_truth: dict[str, Any]) -> GradingResult:
        docs = state.get("extracted_documents", [])
        total_txns = 0
        valid_pointers = 0

        for d in docs:
            for t in getattr(d, "transactions", []):
                total_txns += 1
                sp = t.source_pointer
                if sp and sp.page >= 1 and sp.text_snippet:
                    valid_pointers += 1

        if total_txns == 0:
            return GradingResult(
                grader_name=self.name,
                grader_type=self.grader_type,
                passed=True,
                score=1.0,
                details="No transactions to audit",
            )

        ratio = valid_pointers / total_txns
        passed = ratio >= 0.85

        return GradingResult(
            grader_name=self.name,
            grader_type=self.grader_type,
            passed=passed,
            score=round(ratio, 3),
            details=f"{valid_pointers}/{total_txns} transactions carry valid source pointers",
        )
