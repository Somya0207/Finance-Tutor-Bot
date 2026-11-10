"""Tiny CLI demo for the answer evaluator.  Run:  python main.py"""
from app.errors import AppError
from app.quiz.evaluator import evaluate_answer

question = "What is diversification in investing?"
correct = "Diversification means spreading investments across multiple assets to reduce risk."

if __name__ == "__main__":
    student = input("Enter your answer: ")
    try:
        print("\nEvaluation:\n")
        print(evaluate_answer(question, correct, student, with_score=True))
    except AppError as exc:
        print(f"Error: {exc}")
