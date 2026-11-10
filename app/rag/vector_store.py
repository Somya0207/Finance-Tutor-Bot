"""Build, update and check the persisted Chroma vector store."""
import shutil
from pathlib import Path

from app import config
from app.errors import KnowledgeBaseEmpty
from app.rag.embedding import get_embeddings
from app.rag.loader import load_documents


def split_documents(documents, chunk_size=config.CHUNK_SIZE,
                    chunk_overlap=config.CHUNK_OVERLAP):
    """Split into chunks. chunk_size=None/0 keeps whole documents (eval baseline)."""
    if not chunk_size:
        return list(documents)
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)


def _open_store(persist_directory):
    from app.rag.compat import get_chroma_class

    return get_chroma_class()(persist_directory=str(persist_directory),
                  embedding_function=get_embeddings())


def _reset_store(persist_directory):
    """Empty an existing index. We drop the collection instead of deleting the folder,
    because on Windows Chroma keeps its files open and rmtree raises PermissionError."""
    try:
        _open_store(persist_directory).delete_collection()
    except Exception:
        shutil.rmtree(persist_directory, ignore_errors=True)


def vector_store_exists(persist_directory=config.VECTOR_DB_DIR) -> bool:
    p = Path(persist_directory)
    return p.is_dir() and any(p.iterdir())


def create_vector_store(documents, chunk_size=config.CHUNK_SIZE,
                        chunk_overlap=config.CHUNK_OVERLAP,
                        persist_directory=config.VECTOR_DB_DIR):
    """Create a fresh store (any existing one at that path is replaced)."""
    if not documents:
        raise KnowledgeBaseEmpty(
            "No documents to index. Add .txt, .md, .pdf or .csv files to "
            f"{config.DATA_DIR} (or upload them on the Knowledge Base page)."
        )
    from app.rag.compat import get_chroma_class

    persist_directory = Path(persist_directory)
    if persist_directory.exists():
        _reset_store(persist_directory)  # otherwise reruns add duplicates

    chunks = split_documents(documents, chunk_size, chunk_overlap)
    return get_chroma_class().from_documents(
        chunks,
        embedding=get_embeddings(),
        persist_directory=str(persist_directory),
    )


def add_documents(documents, chunk_size=config.CHUNK_SIZE,
                  chunk_overlap=config.CHUNK_OVERLAP,
                  persist_directory=config.VECTOR_DB_DIR) -> int:
    """Add/refresh documents in the store; re-adding a source replaces its old chunks."""
    if not documents:
        raise KnowledgeBaseEmpty("The file contained no readable text.")
    if not vector_store_exists(persist_directory):
        create_vector_store(documents, chunk_size, chunk_overlap, persist_directory)
        return len(split_documents(documents, chunk_size, chunk_overlap))

    store = _open_store(persist_directory)
    for source in {d.metadata.get("source") for d in documents}:
        old = store.get(where={"source": source}).get("ids", [])
        if old:
            store.delete(ids=old)
    chunks = split_documents(documents, chunk_size, chunk_overlap)
    store.add_documents(chunks)
    return len(chunks)


def ensure_vector_db(persist_directory=config.VECTOR_DB_DIR) -> bool:
    """Build the index from DATA_DIR on first run. Returns True if it built one."""
    if vector_store_exists(persist_directory):
        return False
    create_vector_store(load_documents(), persist_directory=persist_directory)
    return True