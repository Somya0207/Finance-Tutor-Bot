import unittest
from unittest.mock import patch

from app.notes.notes_generator import generate_notes
from app.quiz.evaluator import evaluate_answer


class EvaluatorTests(unittest.TestCase):
    def test_prompt_includes_all_three_inputs_and_no_score_by_default(self):
        with patch("app.llm.llm_model.invoke_llm", return_value="Because...") as m:
            out = evaluate_answer("What is beta?", "Market sensitivity", "Volatility vs market")
        prompt = m.call_args[0][0]
        for s in ["What is beta?", "Market sensitivity", "Volatility vs market", "Do not give a score"]:
            self.assertIn(s, prompt)
        self.assertNotIn("Score out of 10", prompt)
        self.assertEqual(out, "Because...")

    def test_free_text_mode_asks_for_a_score(self):
        with patch("app.llm.llm_model.invoke_llm", return_value="8/10") as m:
            evaluate_answer("q", "a", "b", with_score=True)
        self.assertIn("Score out of 10", m.call_args[0][0])


class NotesTests(unittest.TestCase):
    def test_generates_with_topic(self):
        with patch("app.llm.llm_model.invoke_llm", return_value="NOTES") as m:
            self.assertEqual(generate_notes("  Convexity "), "NOTES")
        self.assertIn("Convexity", m.call_args[0][0])

    def test_blank_topic_rejected_without_llm_call(self):
        with patch("app.llm.llm_model.invoke_llm") as m:
            for bad in ["", "  ", None]:
                with self.assertRaises(ValueError):
                    generate_notes(bad)
            m.assert_not_called()


if __name__ == "__main__":
    unittest.main()
