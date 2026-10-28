import csv
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

CACHE_DIR = Path("data/cache/parsed")


class TableData(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    text: str = ""
    tables: list[TableData] = Field(default_factory=list)
    page_count: int = 0
    parse_status: str = "success"
    file_hash: str = ""


def compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_cached_parse(file_hash: str) -> ParsedDocument | None:
    cache_file = CACHE_DIR / f"{file_hash}.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return ParsedDocument.model_validate(data)
        except Exception:
            return None
    return None


def _save_cached_parse(file_hash: str, parsed: ParsedDocument) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{file_hash}.json"
        cache_file.write_text(parsed.model_dump_json(indent=2), encoding="utf-8")
    except Exception:
        pass


def _fallback_parse(file_path: str, file_hash: str) -> ParsedDocument:
    """Fallback parser for CSV and text documents when Docling is not present."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".csv":
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
            headers = rows[0] if rows else []
            body = rows[1:] if len(rows) > 1 else []
            text_preview = "\n".join([", ".join(r) for r in rows[:50]])
            tables = [TableData(headers=headers, rows=body)] if rows else []
            return ParsedDocument(
                text=text_preview,
                tables=tables,
                page_count=1,
                parse_status="success",
                file_hash=file_hash,
            )
        except Exception:
            pass

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return ParsedDocument(
            text=text[:10000],
            tables=[],
            page_count=1,
            parse_status="success",
            file_hash=file_hash,
        )
    except Exception:
        return ParsedDocument(
            text="",
            tables=[],
            page_count=0,
            parse_status="failed",
            file_hash=file_hash,
        )


def parse_document(file_path: str, use_cache: bool = True) -> ParsedDocument:
    """Parse a document using Docling (or fallback). Uses disk cache keyed by file hash."""
    file_hash = compute_file_hash(file_path)

    if use_cache:
        cached = _get_cached_parse(file_hash)
        if cached:
            return cached

    # Try docling if installed
    try:
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]

        converter = DocumentConverter()
        result = converter.convert(file_path)
        doc = result.document
        text = doc.export_to_markdown() if hasattr(doc, "export_to_markdown") else str(doc)
        tables: list[TableData] = []
        if hasattr(doc, "tables"):
            for t in doc.tables:
                try:
                    df = t.export_to_dataframe()
                    headers = [str(c) for c in df.columns]
                    rows = [[str(cell) for cell in r] for r in df.values.tolist()]
                    tables.append(TableData(headers=headers, rows=rows))
                except Exception:
                    pass
        page_count = getattr(result, "page_count", 0) or 1
        parsed = ParsedDocument(
            text=text,
            tables=tables,
            page_count=page_count,
            parse_status="success",
            file_hash=file_hash,
        )
        if use_cache:
            _save_cached_parse(file_hash, parsed)
        return parsed
    except ImportError:
        # Docling not installed in environment, use robust fallback
        parsed = _fallback_parse(file_path, file_hash)
        if use_cache:
            _save_cached_parse(file_hash, parsed)
        return parsed
    except Exception:
        parsed = ParsedDocument(
            text="",
            tables=[],
            page_count=0,
            parse_status="failed",
            file_hash=file_hash,
        )
        return parsed
