from app.llm import llm_model


def generate_notes(topic):
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Please enter a topic first.")

    prompt = f"""
    Create structured study notes about {topic}

    Include:
    - Definition
    - Key concepts
    - Examples
    - Important points for exams

    Formatting rules:
    - Keep it concise (about 400-600 words) and finish every section.
    - Write formulas in LaTeX between single dollar signs, like $D = \\frac{{a}}{{b}}$.
      Do not use backslash-parenthesis or backslash-bracket delimiters.
    """
    return llm_model.invoke_llm(prompt)