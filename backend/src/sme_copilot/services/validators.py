from datetime import datetime
from typing import Any

from sme_copilot.schemas.models import (
    CheckResult,
    ExtractedDocument,
    ValidationCheck,
    ValidationResult,
)


def running_balance_check(transactions: list[dict[str, Any]]) -> CheckResult:
    """Check that each transaction's balance = previous balance + amount."""
    if not transactions:
        return CheckResult(
            check_name=ValidationCheck.RUNNING_BALANCE.value,
            passed=True,
            details="No transactions",
        )
    prev_balance = None
    for i, tx in enumerate(transactions):
        amount = tx.get("amount", 0)
        balance = tx.get("balance")
        if balance is None:
            continue
        if prev_balance is not None:
            expected = round(prev_balance + amount, 2)
            if round(balance, 2) != expected:
                return CheckResult(
                    check_name=ValidationCheck.RUNNING_BALANCE.value,
                    passed=False,
                    details=f"Mismatch at row {i}: expected {expected}, got {balance}",
                )
        prev_balance = balance
    return CheckResult(check_name=ValidationCheck.RUNNING_BALANCE.value, passed=True, details="OK")


def line_item_sum_check(items: list[dict[str, Any]], stated_total: float) -> CheckResult:
    """Check that line items sum to stated total."""
    computed = round(sum(item.get("amount", 0) for item in items), 2)
    if round(stated_total, 2) != computed:
        return CheckResult(
            check_name=ValidationCheck.LINE_ITEM_SUM.value,
            passed=False,
            details=f"Stated total {stated_total} != computed {computed}",
        )
    return CheckResult(check_name=ValidationCheck.LINE_ITEM_SUM.value, passed=True, details="OK")


def date_continuity_check(
    transactions: list[dict[str, Any]], max_gap_days: int = 30
) -> CheckResult:
    """Check no gaps > max_gap_days between transaction dates (warning)."""
    dates = []
    for tx in transactions:
        d = tx.get("date")
        if d:
            try:
                dates.append(datetime.fromisoformat(str(d).replace("Z", "+00:00")))
            except ValueError:
                pass
    if len(dates) < 2:
        return CheckResult(
            check_name=ValidationCheck.DATE_CONTINUITY.value,
            passed=True,
            details="Insufficient dates",
        )
    dates.sort()
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        if gap > max_gap_days:
            return CheckResult(
                check_name=ValidationCheck.DATE_CONTINUITY.value,
                passed=False,
                details=f"Gap of {gap} days between {dates[i-1].date()} and {dates[i].date()}",
            )
    return CheckResult(check_name=ValidationCheck.DATE_CONTINUITY.value, passed=True, details="OK")


def run_validation(
    transactions: list[dict[str, Any]], stated_total: float | None = None
) -> ValidationResult:
    checks = [
        running_balance_check(transactions),
        date_continuity_check(transactions),
    ]
    if stated_total is not None:
        checks.append(line_item_sum_check(transactions, stated_total))
    passed = all(c.passed for c in checks)
    errors = [c.details for c in checks if not c.passed]
    return ValidationResult(
        application_id="",
        checks=checks,
        passed=passed,
        errors=errors,
    )


class ValidationService:
    @staticmethod
    def validate_extracted_document(doc: ExtractedDocument) -> ValidationResult:
        tx_dicts = [
            {"date": t.date, "amount": t.amount, "balance": t.balance} for t in doc.transactions
        ]
        stated_total = None
        if "total" in doc.summary_fields and isinstance(doc.summary_fields["total"], (int, float)):
            stated_total = float(doc.summary_fields["total"])

        vr = run_validation(tx_dicts, stated_total=stated_total)
        vr.application_id = doc.application_id
        return vr

    @classmethod
    def validate_documents(
        cls, documents: list[ExtractedDocument]
    ) -> tuple[list[ValidationResult], float, list[str]]:
        """Validate all extracted documents.

        Returns: (validation_results, composite_confidence, fraud_flags)
        """
        results: list[ValidationResult] = []
        fraud_flags: list[str] = []
        confidence = 0.95

        for doc in documents:
            if doc.extraction_status == "failed":
                fraud_flags.append(f"Document {doc.file_ref.filename} failed extraction")
                confidence = min(confidence, 0.5)
                continue

            vr = cls.validate_extracted_document(doc)
            results.append(vr)

            if not vr.passed:
                confidence = min(confidence, 0.6)
                for err in vr.errors:
                    fname = doc.file_ref.filename
                    if "Mismatch" in err:
                        fraud_flags.append(f"Running balance mismatch in {fname}: {err}")
                    elif "Gap" in err:
                        fraud_flags.append(f"Continuity anomaly in {fname}: {err}")
                    else:
                        fraud_flags.append(f"Discrepancy in {fname}: {err}")

        return results, round(confidence, 2), fraud_flags
