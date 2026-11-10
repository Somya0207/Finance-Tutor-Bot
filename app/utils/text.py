"""Small text helpers shared by the app."""
import io
import re


def extract_pdf_text(file_like) -> str:
    """Extract text from a PDF (path or binary file object). Never returns None."""
    try:
        from pypdf import PdfReader
    except ImportError:  # older environments
        from PyPDF2 import PdfReader

    reader = PdfReader(file_like)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")  # extract_text can return None
    return "\n".join(parts).strip()


def pdf_bytes_to_text(data: bytes) -> str:
    return extract_pdf_text(io.BytesIO(data))


# ---------------------------------------------------------------- math for Streamlit
# Streamlit renders math written as $...$ / $$...$$, but LLMs often write \( ... \) and
# \[ ... \], which Streamlit shows as broken text. We convert them, and escape money
# amounts like "$100" so two of them are not mistaken for one formula.
_MONEY = re.compile(r"(?<!\\)\$(?=\d[\d,]*(?:\.\d+)?(?![\w^_{\\]))")
_PAREN_MATH = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_BRACKET_MATH = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)


def fix_math(text) -> str:
    if not text:
        return ""
    text = _MONEY.sub(r"\\$", text)
    text = _BRACKET_MATH.sub(lambda m: f"$${m.group(1).strip()}$$", text)
    text = _PAREN_MATH.sub(lambda m: f"${m.group(1).strip()}$", text)
    return text