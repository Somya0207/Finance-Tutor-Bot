from app.rag.retriever import get_retriever
from app.llm.llm_model import get_llm

retriever = get_retriever()
llm = get_llm()

def finance_chat(question):

    docs = retriever.invoke(question)

    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"""
Use the following finance knowledge to answer the question.

Context:
{context}

Question:
{question}
"""

    response = llm.invoke(prompt)

    return response.content