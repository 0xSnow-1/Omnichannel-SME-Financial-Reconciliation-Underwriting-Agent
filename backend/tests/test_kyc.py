import os

from sme_copilot.services.kyc import KYCService


def test_kyc_pass_default():
    os.environ["KYC_STUB_RESULT"] = "pass"
    svc = KYCService()
    result = svc.check("m1")
    assert result.passed is True


def test_kyc_fail_default():
    os.environ["KYC_STUB_RESULT"] = "fail"
    svc = KYCService()
    result = svc.check("m1")
    assert result.passed is False


def test_kyc_override():
    os.environ["KYC_STUB_RESULT"] = "pass"
    svc = KYCService()
    result = svc.check("m1", override="fail")
    assert result.passed is False
