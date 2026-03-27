from app.rag.retriever import get_retriever
from app.llm.llm_model import get_llm

retriever = get_retriever()
llm = get_llm()

def ask_tutor(question):

    docs = retriever.invoke(question)

    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"""
You are a finance tutor helping a student.

Use the following context to answer the question clearly.

Context:
{context}

Question:
{question}

Explain in simple terms.
"""

    response = llm.invoke(prompt)

    return response.content