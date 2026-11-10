from app import config
from app.errors import KnowledgeBaseEmpty
from app.rag.vector_store import _open_store, vector_store_exists


def get_retriever(persist_directory=config.VECTOR_DB_DIR, k=config.TOP_K):
    if not vector_store_exists(persist_directory):
        raise KnowledgeBaseEmpty(
            f"No vector index found at {persist_directory}. "
            "Run `python build_db.py` or add documents on the Knowledge Base page."
        )
    return _open_store(persist_directory).as_retriever(search_kwargs={"k": k})
