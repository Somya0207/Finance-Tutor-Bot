"""Groq LLM client with automatic fallback when a model has been retired.

Heavy imports are lazy so the rest of the app is importable (and unit-testable)
without langchain installed."""
import json
import urllib.request
from functools import lru_cache

from app import config
from app.errors import LLMConfigError, LLMError

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

# Tried in this order when the configured model is not available.
PREFERRED_MODELS = [
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
]
NON_CHAT_HINTS = ("whisper", "tts", "guard", "embed", "orpheus", "playai", "compound")

_active_model = None  # set when we had to switch away from config.LLM_MODEL


def current_model() -> str:
    return _active_model or config.LLM_MODEL


@lru_cache(maxsize=1)
def get_llm():
    api_key = config.get_groq_api_key()
    if not api_key:
        raise LLMConfigError(
            "No Groq API key found. Add GROQ_API=<your key> to a .env file "
            "(or to Streamlit secrets) and restart the app."
        )
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=current_model(),
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
        groq_api_key=api_key,
    )


def list_available_models(api_key) -> list:
    """Ask Groq which models this key can use. Returns [] if the request fails."""
    try:
        req = urllib.request.Request(
            GROQ_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return [m["id"] for m in json.load(resp).get("data", [])]
    except Exception:
        return []


def pick_model(requested, available):
    """Choose the requested model if available, else the best chat model on the list."""
    if requested in available:
        return requested
    for name in PREFERRED_MODELS:
        if name in available:
            return name
    for name in available:
        if not any(h in name.lower() for h in NON_CHAT_HINTS):
            return name
    return None


def _is_model_error(exc) -> bool:
    text = str(exc).lower()
    return any(s in text for s in ("model_not_found", "decommissioned",
                                   "does not exist", "no longer supported"))


def _switch_to_available_model() -> bool:
    """Switch to a model Groq still serves. Returns True if we changed model."""
    global _active_model
    available = list_available_models(config.get_groq_api_key())
    choice = pick_model(current_model(), available)
    if not choice or choice == current_model():
        return False
    _active_model = choice
    get_llm.cache_clear()
    return True


def invoke_llm(prompt: str) -> str:
    """Send a prompt to the LLM and return the text. Raises LLMError/LLMConfigError."""
    llm = get_llm()
    try:
        response = llm.invoke(prompt)
    except Exception as exc:
        if not (_is_model_error(exc) and _switch_to_available_model()):
            raise LLMError(f"The language model request failed: {exc}") from exc
        try:  # retry once on the new model
            response = get_llm().invoke(prompt)
        except Exception as exc2:
            raise LLMError(f"The language model request failed: {exc2}") from exc2

    text = getattr(response, "content", str(response))
    meta = getattr(response, "response_metadata", None) or {}
    if meta.get("finish_reason") == "length":
        text += "\n\n*⚠️ This answer was cut off by the length limit. Ask again with a narrower question.*"
    return text