from app.llm.llm_model import get_llm

llm = get_llm()

def generate_notes(topic):

    prompt = f"""
    Create structured study notes about {topic}

    Include:
    - Definition
    - Key concepts
    - Examples
    - Important points for exams
    """

    response = llm.invoke(prompt)

    return response.content