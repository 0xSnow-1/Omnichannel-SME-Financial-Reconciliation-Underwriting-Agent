import hashlib
import json

from sme_copilot.schemas.models import AuditEntry


def compute_hash(prev_hash: str, entry: AuditEntry) -> str:
    payload = entry.model_dump(mode="json")
    payload.pop("entry_hash", None)
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256((prev_hash + serialized).encode()).hexdigest()


def verify_chain(entries: list[AuditEntry]) -> bool:
    for i, entry in enumerate(entries):
        expected_prev = entries[i - 1].entry_hash if i > 0 else ""
        if entry.prev_hash != expected_prev:
            return False
        if entry.entry_hash != compute_hash(entry.prev_hash, entry):
            return False
    return True
