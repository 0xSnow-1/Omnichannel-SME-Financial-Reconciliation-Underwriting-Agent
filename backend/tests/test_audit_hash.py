from sme_copilot.schemas.models import AuditEntry
from sme_copilot.services.audit import compute_hash, verify_chain


def test_hash_computation():
    entry = AuditEntry(application_id="1", action="create", actor="system")
    entry.entry_hash = compute_hash("", entry)
    assert len(entry.entry_hash) == 64


def test_chain_integrity():
    e1 = AuditEntry(application_id="1", action="create", actor="system")
    e1.entry_hash = compute_hash("", e1)
    e1.prev_hash = ""
    e2 = AuditEntry(
        application_id="1", action="review", actor="underwriter", prev_hash=e1.entry_hash
    )
    e2.entry_hash = compute_hash(e1.entry_hash, e2)
    assert verify_chain([e1, e2]) is True


def test_tamper_detection():
    e1 = AuditEntry(application_id="1", action="create", actor="system")
    e1.entry_hash = compute_hash("", e1)
    e1.prev_hash = ""
    e2 = AuditEntry(
        application_id="1", action="review", actor="underwriter", prev_hash=e1.entry_hash
    )
    e2.entry_hash = compute_hash(e1.entry_hash, e2)
    e2.action = "tampered"
    assert verify_chain([e1, e2]) is False
