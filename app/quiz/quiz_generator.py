import json
from app.llm.llm_model import get_llm

llm = get_llm()

def generate_quiz(topic, report_text=None, difficulty="medium", num_questions=5):


    context = ""
    if report_text:
        context = f"\nUse this report as context:\n{report_text[:2000]}"

    prompt = f"""
    You are a finance professor creating quizzes.

    Topic: {topic}

    Difficulty Level: {difficulty}

    {context}

    Generate {num_questions} multiple choice questions.

    Difficulty Rules:
    - easy → basic definitions
    - medium → conceptual understanding
    - hard → analytical / case-based questions

    Return ONLY valid JSON.

    Format:

    [
    {{
    "question": "Question text",
    "options": ["Option A","Option B","Option C","Option D"],
    "answer": "Correct option",
    "explanation": "Short explanation"
    }}
    ]

    No extra text.
    """
    
    response = llm.invoke(prompt)

    content = response.content.strip()

    # remove markdown formatting if model adds it
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]

    if "```" in content:
        content = content.replace("```", "")

    content = content.strip()

    try:
        quiz = json.loads(content)
        return quiz

    except Exception as e:
        print("JSON ERROR:", e)
        print("MODEL OUTPUT:", content)
        return []