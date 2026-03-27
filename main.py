from app.quiz.evaluator import evaluate_answer

question = "What is diversification in investing?"
correct = "Diversification means spreading investments across multiple assets to reduce risk."

student = input("Enter your answer: ")

result = evaluate_answer(question, correct, student)

print("\nEvaluation:\n")
print(result)