"""Rebuild the Chroma vector index from every file in data/investment_reports/."""
from app.rag.loader import load_documents
from app.rag.vector_store import create_vector_store

if __name__ == "__main__":
    print("Loading documents...")
    docs = load_documents()
    print(f"Loaded {len(docs)} document(s). Creating vector database...")
    create_vector_store(docs)
    print("Vector database created!")
