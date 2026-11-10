import json
import unittest
from unittest.mock import patch

from app.quiz import quiz_generator as qg

GOOD = [{"question": "What is a bond?", "options": ["A loan", "A share", "A swap", "A fund"],
         "answer": "A loan", "explanation": "Bonds are loans."}]


class ParseTests(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(qg.parse_quiz_json(json.dumps(GOOD)), GOOD)

    def test_fenced_json_with_prose(self):
        text = "Sure! Here you go:\n```json\n" + json.dumps(GOOD) + "\n```\nHope it helps"
        self.assertEqual(qg.parse_quiz_json(text), GOOD)

    def test_garbage_returns_empty(self):
        self.assertEqual(qg.parse_quiz_json("not json at all"), [])
        self.assertEqual(qg.parse_quiz_json("[1, 2,"), [])
        self.assertEqual(qg.parse_quiz_json(""), [])
        self.assertEqual(qg.parse_quiz_json(None), [])


class ValidateTests(unittest.TestCase):
    def test_drops_malformed_items(self):
        items = GOOD + [{"question": "no options", "answer": "x"},
                        {"question": "one option", "options": ["a"], "answer": "a"},
                        "string", None, {"options": ["a", "b"], "answer": "a"}]
        self.assertEqual(len(qg.validate_quiz(items)), 1)

    def test_missing_explanation_defaults_empty(self):
        item = {"question": "q", "options": ["a", "b"], "answer": "a"}
        self.assertEqual(qg.validate_quiz([item])[0]["explanation"], "")


class ResolveTests(unittest.TestCase):
    OPTS = ["Alpha", "Beta", "Gamma", "Delta"]

    def q(self, answer):
        return {"question": "?", "options": self.OPTS, "answer": answer, "explanation": ""}

    def test_letter_forms(self):
        for form in ["B", "b", "B)", "(B)", "B.", "Option B", "option b"]:
            self.assertEqual(qg.resolve_correct_option(self.q(form)), "Beta", form)

    def test_full_text(self):
        self.assertEqual(qg.resolve_correct_option(self.q("gamma")), "Gamma")

    def test_unknown_answer_returned_as_is(self):
        self.assertEqual(qg.resolve_correct_option(self.q("Epsilon")), "Epsilon")

    def test_is_correct(self):
        self.assertTrue(qg.is_correct(self.q("C"), " gamma "))
        self.assertFalse(qg.is_correct(self.q("C"), "Alpha"))
        self.assertFalse(qg.is_correct(self.q("C"), None))


class GenerateTests(unittest.TestCase):
    def test_retries_after_bad_output(self):
        replies = iter(["oops, no json", json.dumps(GOOD)])
        with patch("app.llm.llm_model.invoke_llm", side_effect=lambda p: next(replies)):
            self.assertEqual(len(qg.generate_quiz("bonds")), 1)

    def test_gives_up_after_attempts(self):
        with patch("app.llm.llm_model.invoke_llm", return_value="nope") as m:
            self.assertEqual(qg.generate_quiz("bonds", attempts=2), [])
            self.assertEqual(m.call_count, 2)

    def test_prompt_contains_topic_difficulty_and_truncated_report(self):
        with patch("app.llm.llm_model.invoke_llm", return_value=json.dumps(GOOD)) as m:
            qg.generate_quiz("Duration", report_text="X" * 5000, difficulty="hard", num_questions=3)
        prompt = m.call_args[0][0]
        self.assertIn("Duration", prompt)
        self.assertIn("hard", prompt)
        self.assertIn("Generate 3 multiple choice", prompt)
        self.assertLessEqual(prompt.count("X"), 2000)

    def test_question_count_is_clamped(self):
        with patch("app.llm.llm_model.invoke_llm", return_value=json.dumps(GOOD)) as m:
            qg.generate_quiz("t", num_questions=999)
        self.assertIn("Generate 20 multiple choice", m.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
