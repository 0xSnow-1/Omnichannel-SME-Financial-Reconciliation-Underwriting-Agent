import hashlib

from pydantic import BaseModel, Field


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


def parse_document(file_path: str) -> ParsedDocument:
    """Parse a document using Docling. Falls back gracefully on failure."""
    file_hash = compute_file_hash(file_path)
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)
        doc = result.document
        text = doc.export_to_markdown() if hasattr(doc, "export_to_markdown") else str(doc)
        tables: list[TableData] = []
        if hasattr(doc, "tables"):
            for t in doc.tables:
                try:
                    df = t.export_to_dataframe()
                    headers = list(df.columns)
                    rows = [list(r) for r in df.values.tolist()]
                    tables.append(TableData(headers=headers, rows=rows))
                except Exception:
                    pass
        page_count = getattr(result, "page_count", 0) or 0
        return ParsedDocument(
            text=text,
            tables=tables,
            page_count=page_count,
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
