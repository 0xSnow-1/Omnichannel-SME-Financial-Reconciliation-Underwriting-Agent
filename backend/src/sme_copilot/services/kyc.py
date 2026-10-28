import os

from sme_copilot.schemas.models import KYCResult


class KYCService:
    def __init__(self) -> None:
        self._default = os.getenv("KYC_STUB_RESULT", "pass")

    def check(self, merchant_id: str, override: str | None = None) -> KYCResult:
        result = override if override is not None else self._default
        passed = result.strip().lower() == "pass"
        reason = "Stub KYC check passed" if passed else "Stub KYC check failed"
        return KYCResult(passed=passed, reason=reason)
