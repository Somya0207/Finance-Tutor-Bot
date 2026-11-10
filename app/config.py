"""Central configuration. All paths are absolute so the app works from any cwd."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Knowledge base source documents and the persisted Chroma index
DATA_DIR = Path(os.getenv("FTB_DATA_DIR", PROJECT_ROOT / "data" / "investment_reports"))
VECTOR_DB_DIR = Path(os.getenv("FTB_VECTOR_DB_DIR", PROJECT_ROOT / "vector_db"))

# SQLite file for users and quiz history
APP_DB_PATH = Path(os.getenv("FTB_APP_DB", PROJECT_ROOT / "app_data" / "finance_tutor.db"))

# Retrieval settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
TOP_K = 4
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# LLM settings (override the model with FTB_MODEL if Groq retires it)
LLM_MODEL = os.getenv("FTB_MODEL", "llama-3.1-8b-instant")
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = int(os.getenv("FTB_MAX_TOKENS", "8192"))  # reasoning models spend tokens thinking

# Prompt size guards (characters)
MAX_REPORT_CHARS = 3000
MAX_QUIZ_REPORT_CHARS = 2000

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".csv"}


def get_groq_api_key():
    """Return the Groq key from env (.env), or Streamlit secrets, or None."""
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("GROQ_API") or os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:  # Streamlit Community Cloud keeps secrets in st.secrets
        import streamlit as st

        return st.secrets.get("GROQ_API") or st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


def login_required():
    return os.getenv("REQUIRE_LOGIN", "").strip().lower() in {"1", "true", "yes"}
