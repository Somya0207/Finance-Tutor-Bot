from langchain_community.vectorstores import Chroma
from app.rag.embedding import get_embeddings

def get_retriever():

    embeddings = get_embeddings()

    vectordb = Chroma(
        persist_directory="vector_db",
        embedding_function=embeddings
    )

    retriever = vectordb.as_retriever()

    return retriever