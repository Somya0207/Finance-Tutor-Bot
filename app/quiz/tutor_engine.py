"""RAG question answering shared by the Ask page and the chatbot."""
from app import config
from app.llm import llm_model
from app.rag.retriever import get_retriever
from app.rag.vector_store import ensure_vector_db

DEFAULT_STYLE = "Explain in simple terms."


def _format_history(history, max_turns=6):
    if not history:
        return ""
    lines = []
    for m in history[-max_turns * 2:]:
        who = "Student" if m.get("role") == "user" else "Tutor"
        lines.append(f"{who}: {m.get('content', '')}")
    return "Conversation so far:\n" + "\n".join(lines) + "\n\n"


def build_prompt(question, docs, report_context=None, style=DEFAULT_STYLE, history=None):
    kb_context = "\n\n".join(
        f"[{i}] (source: {(d.metadata or {}).get('source', 'unknown')})\n{d.page_content}"
        for i, d in enumerate(docs, 1)
    ) or "(no matching passages found)"
    report_block = ""
    if report_context:
        report_block = f"\nUploaded report excerpts:\n{report_context[:config.MAX_REPORT_CHARS]}\n"
    return f"""You are a finance tutor helping a student.
Answer using the knowledge base passages below and cite them like [1] when you use them.
If they do not contain the answer, say so briefly, then answer from general finance knowledge.

Knowledge base:
{kb_context}
{report_block}
{_format_history(history)}Question: {question}

{style}"""


def ask_tutor(question, report_context=None, style=DEFAULT_STYLE, history=None):
    """Return (answer_text, retrieved_docs). Raises AppError subclasses on failure."""
    question = (question or "").strip()
    if not question:
        raise ValueError("Please enter a question first.")

    ensure_vector_db()  # builds the index from data/ on first run
    docs = get_retriever().invoke(question)  # search with the clean question only
    answer = llm_model.invoke_llm(
        build_prompt(question, docs, report_context, style, history)
    )
    return answer, docs
