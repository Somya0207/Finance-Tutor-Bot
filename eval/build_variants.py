"""Build one vector DB per chunking strategy for the retrieval evaluation.
Run from the project root:  python -m eval.build_variants"""
from app import config
from app.rag.loader import load_documents
from app.rag.vector_store import create_vector_store

VARIANTS = {
    "vector_db_none": dict(chunk_size=None, chunk_overlap=0),
    "vector_db_500": dict(chunk_size=500, chunk_overlap=50),
    "vector_db_1000": dict(chunk_size=1000, chunk_overlap=100),
}

if __name__ == "__main__":
    docs = load_documents()
    for name, cfg in VARIANTS.items():
        create_vector_store(docs, persist_directory=config.PROJECT_ROOT / name, **cfg)
        print("built", name)
