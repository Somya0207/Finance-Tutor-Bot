from app.rag.loader import load_documents
from app.rag.vector_store import create_vector_store

print("Loading documents...")

docs = load_documents()

print("Creating vector database...")

create_vector_store(docs)

print("Vector database created!")