"""Load knowledge-base files (.txt, .md, .pdf, .csv) from disk."""
import csv
from pathlib import Path

from app import config
from app.utils.text import extract_pdf_text


def _read_csv(path: Path) -> str:
    """Turn each CSV row into a readable 'column: value' line."""
    lines = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cells = [f"{k.strip()}: {str(v).strip()}" for k, v in row.items()
                     if k and v not in (None, "")]
            if cells:
                lines.append("; ".join(cells))
    return "\n".join(lines)


def read_file_text(path) -> str:
    """Return the plain text of a supported file ('' if unsupported or empty)."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    if ext == ".pdf":
        return extract_pdf_text(str(path))
    if ext == ".csv":
        return _read_csv(path).strip()
    return ""


def list_source_files(folder=None):
    folder = Path(folder or config.DATA_DIR)
    if not folder.exists():
        return []
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and p.suffix.lower() in config.SUPPORTED_EXTENSIONS)


def load_file(path, folder=None):
    """Load one file as a list of LangChain Documents (empty list if no text)."""
    from langchain_core.documents import Document

    path = Path(path)
    text = read_file_text(path)
    if not text:
        return []
    base = Path(folder or config.DATA_DIR)
    try:
        source = path.relative_to(base).as_posix()
    except ValueError:
        source = path.name
    return [Document(page_content=text, metadata={"source": source})]


def load_documents(folder=None):
    """Load every supported, non-empty file in the knowledge-base folder."""
    docs = []
    for path in list_source_files(folder):
        docs.extend(load_file(path, folder))
    return docs
