"""Import the LangChain integrations from whichever package is installed.

LangChain 1.x ships Chroma and HuggingFace embeddings in dedicated packages
(`langchain-chroma`, `langchain-huggingface`). Older setups have them in
`langchain-community`. We prefer the dedicated packages and fall back.
"""


def get_chroma_class():
    try:
        from langchain_chroma import Chroma
        return Chroma
    except ImportError:
        pass
    try:
        from langchain_community.vectorstores import Chroma
        return Chroma
    except ImportError as exc:
        raise ImportError(
            "Chroma integration not installed. Run: pip install langchain-chroma"
        ) from exc


def get_hf_embeddings_class():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings
    except ImportError:
        pass
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings
    except ImportError as exc:
        raise ImportError(
            "HuggingFace embeddings not installed. Run: pip install langchain-huggingface"
        ) from exc


def release_chroma():
    """Drop Chroma's cached clients so its files can be deleted (needed on Windows)."""
    import gc

    for module in ("chromadb.api.shared_system_client", "chromadb.api.client"):
        try:
            mod = __import__(module, fromlist=["SharedSystemClient"])
            mod.SharedSystemClient.clear_system_cache()
            break
        except Exception:
            continue
    gc.collect()