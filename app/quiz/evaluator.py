from app.llm import llm_model


def evaluate_answer(question, correct_answer, user_answer, with_score=False):
    """LLM feedback on a wrong answer. Set with_score=True for free-text answers (CLI demo)."""
    if with_score:
        task = """Evaluate the answer.

    Give:
    1. Score out of 10
    2. Explanation
    3. Correct concept if the student is wrong"""
    else:
        task = """The student got this multiple-choice question wrong.
    In 2-3 short sentences, explain why their answer is wrong and why the correct answer is right.
    Do not give a score and do not repeat the question."""

    prompt = f"""
    You are a friendly finance tutor.

    Question:
    {question}

    Correct Answer:
    {correct_answer}

    Student Answer:
    {user_answer}

    {task}
    """
    return llm_model.invoke_llm(prompt)