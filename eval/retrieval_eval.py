"""Compare retrieval quality across chunking strategies (hit@k, MRR, context size).

    python -m eval.build_variants
    python -m eval.retrieval_eval
"""
import json
import sys

from app import config
from app.rag.retriever import get_retriever

VARIANTS = ["vector_db_none", "vector_db_500", "vector_db_1000"]
K = 4
QUESTIONS_PATH = config.PROJECT_ROOT / "eval" / "questions.jsonl"


def _norm(text):
    return " ".join(text.lower().split())


def load_questions(path=QUESTIONS_PATH):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def find_bad_questions(questions, data_dir=config.DATA_DIR):
    """Return questions whose source file is missing or doesn't contain the key fact."""
    bad = []
    for q in questions:
        path = data_dir / q["source"]
        if not path.exists():
            bad.append((q, "source file not found"))
        elif _norm(q["key_fact"]) not in _norm(path.read_text(encoding="utf-8")):
            bad.append((q, "key fact not in source"))
    return bad


def check_questions(questions):
    bad = find_bad_questions(questions)
    for q, why in bad:
        print(f"{why.upper()}: {q['question']}")
    if bad:
        sys.exit("Fix the questions above first.")


def score_results(retrieved_per_question, questions, k=K):
    """retrieved_per_question: list of lists of chunk texts, aligned with questions."""
    hits, rr_sum, chars = 0, 0.0, 0
    for texts, q in zip(retrieved_per_question, questions):
        chars += sum(len(t) for t in texts)
        rank = next((i for i, t in enumerate(texts, 1)
                     if _norm(q["key_fact"]) in _norm(t)), None)
        if rank:
            hits += 1
            rr_sum += 1 / rank
    n = len(questions)
    return {f"hit@{k}": round(hits / n, 3), "MRR": round(rr_sum / n, 3),
            "avg_context_chars": round(chars / n)}


def evaluate(variant, questions, k=K):
    retriever = get_retriever(persist_directory=config.PROJECT_ROOT / variant, k=k)
    retrieved = [[d.page_content for d in retriever.invoke(q["question"])]
                 for q in questions]  # clean question only
    return {"variant": variant, **score_results(retrieved, questions, k)}


if __name__ == "__main__":
    questions = load_questions()
    check_questions(questions)
    print(f"{len(questions)} questions")
    for v in VARIANTS:
        if not (config.PROJECT_ROOT / v).exists():
            sys.exit(f"{v} not found - run `python -m eval.build_variants` first.")
        print(evaluate(v, questions))
