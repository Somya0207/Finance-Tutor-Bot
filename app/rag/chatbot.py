from app.quiz.tutor_engine import ask_tutor


def finance_chat(question, history=None, report_context=None):
    """Conversational RAG answer. Returns (answer_text, retrieved_docs)."""
    return ask_tutor(
        question,
        report_context=report_context,
        style="Answer conversationally and concisely.",
        history=history,
    )
