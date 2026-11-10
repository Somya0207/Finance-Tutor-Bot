import json
import re

from app import config
from app.llm import llm_model

LETTERS = "ABCD"


def parse_quiz_json(content: str):
    """Extract a JSON list from model output (handles ``` fences and extra prose)."""
    content = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def validate_quiz(items):
    """Keep only well-formed questions; normalise fields to strings."""
    valid = []
    for q in items:
        if not isinstance(q, dict):
            continue
        options = q.get("options")
        if (not q.get("question") or not q.get("answer")
                or not isinstance(options, list) or len(options) < 2):
            continue
        valid.append({
            "question": str(q["question"]).strip(),
            "options": [str(o).strip() for o in options],
            "answer": str(q["answer"]).strip(),
            "explanation": str(q.get("explanation", "")).strip(),
        })
    return valid


def resolve_correct_option(q) -> str:
    """Return the text of the correct option even if the model answered 'B', 'B)' or 'Option B'."""
    answer, options = q["answer"].strip(), q["options"]
    m = re.fullmatch(r"(?:option\s*)?\(?([A-D])\)?[.)]?", answer, re.IGNORECASE)
    if m:
        idx = LETTERS.index(m.group(1).upper())
        if idx < len(options):
            return options[idx]
    lowered = answer.lower()
    for opt in options:  # the model gave the option text itself
        if opt.lower() == lowered:
            return opt
    return answer


def is_correct(q, user_answer) -> bool:
    return (user_answer or "").strip().lower() == resolve_correct_option(q).strip().lower()


def _build_prompt(topic, report_text, difficulty, num_questions):
    context = ""
    if report_text:
        context = f"\nUse this report as context:\n{report_text[:config.MAX_QUIZ_REPORT_CHARS]}"
    return f"""
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
    "answer": "Correct option (the full option text)",
    "explanation": "Short explanation"
    }}
    ]

    No extra text.
    """


def generate_quiz(topic, report_text=None, difficulty="medium", num_questions=5, attempts=2):
    """Return a validated list of questions ([] if the model never produced valid JSON)."""
    num_questions = max(1, min(int(num_questions), 20))
    prompt = _build_prompt(topic, report_text, difficulty, num_questions)
    for _ in range(attempts):
        quiz = validate_quiz(parse_quiz_json(llm_model.invoke_llm(prompt)))
        if quiz:
            return quiz[:num_questions]
    return []
