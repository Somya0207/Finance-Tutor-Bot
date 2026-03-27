from langchain_community.vectorstores import Chroma
from app.rag.embedding import get_embeddings


def create_vector_store(documents):

    embeddings = get_embeddings()

    vectordb = Chroma.from_documents(
        documents,
        embedding=embeddings,
        persist_directory="vector_db"
    )

    vectordb.persist()

    return vectordb