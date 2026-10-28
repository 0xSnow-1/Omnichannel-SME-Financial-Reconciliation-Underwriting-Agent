from pathlib import Path

import pytest
from sme_copilot.services.docling_parser import (
    _fallback_parse,
    _get_cached_parse,
    compute_file_hash,
    parse_document,
)


def test_compute_file_hash(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("hello world")
    h = compute_file_hash(str(f))
    assert len(h) == 64


def test_fallback_parse_csv(tmp_path: Path):
    csv_file = tmp_path / "statement.csv"
    csv_file.write_text(
        "Date,Description,Amount,Balance\n"
        "2024-01-01,Deposit,1000.00,1000.00\n"
        "2024-01-02,Withdrawal,-200.00,800.00\n"
    )
    parsed = _fallback_parse(str(csv_file), "dummy_hash")
    assert parsed.parse_status == "success"
    assert len(parsed.tables) == 1
    assert parsed.tables[0].headers == ["Date", "Description", "Amount", "Balance"]
    assert len(parsed.tables[0].rows) == 2


def test_fallback_parse_text(tmp_path: Path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Simple text file content")
    parsed = _fallback_parse(str(txt_file), "dummy_hash")
    assert parsed.parse_status == "success"
    assert "Simple text" in parsed.text


def test_fallback_parse_nonexistent():
    parsed = _fallback_parse("/nonexistent/path/file.xyz", "dummy_hash")
    assert parsed.parse_status == "failed"


def test_parse_caching(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import sme_copilot.services.docling_parser as dp

    monkeypatch.setattr(dp, "CACHE_DIR", tmp_path / "cache")

    test_file = tmp_path / "test.csv"
    test_file.write_text("Date,Amount\n2024-01-01,100\n")

    # First parse: creates cache
    p1 = parse_document(str(test_file), use_cache=True)
    assert p1.parse_status == "success"

    # Cached retrieval
    cached = _get_cached_parse(p1.file_hash)
    assert cached is not None
    assert cached.file_hash == p1.file_hash

    # Second parse uses cache
    p2 = parse_document(str(test_file), use_cache=True)
    assert p2.file_hash == p1.file_hash


def test_cache_corrupt_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import sme_copilot.services.docling_parser as dp

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dp, "CACHE_DIR", cache_dir)

    corrupt_file = cache_dir / "badhash.json"
    corrupt_file.write_text("{bad json")

    assert _get_cached_parse("badhash") is None
