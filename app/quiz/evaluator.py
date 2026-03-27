from app.llm.llm_model import get_llm

llm = get_llm()

def evaluate_answer(question, correct_answer, user_answer):

    prompt = f"""
    You are a finance tutor evaluating a student's answer.

    Question:
    {question}

    Correct Answer:
    {correct_answer}

    Student Answer:
    {user_answer}

    Evaluate the answer.

    Give:
    1. Score out of 10
    2. Explanation
    3. Correct concept if the student is wrong
    """

    response = llm.invoke(prompt)

    return response.content