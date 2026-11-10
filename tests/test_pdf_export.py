import io
import unittest

from app.utils.pdf_export import notes_to_pdf, quiz_results_to_pdf
from app.utils.text import extract_pdf_text


class PdfExportTests(unittest.TestCase):
    def test_notes_pdf_is_valid_and_contains_text(self):
        notes = "# Bonds\n**Key Concepts**\nI. Definition\n- Coupon & face value\n* Risk <high>\n\n1. Duration"
        pdf = notes_to_pdf(notes)
        self.assertTrue(pdf.startswith(b"%PDF"))
        text = extract_pdf_text(io.BytesIO(pdf))
        self.assertIn("Coupon & face value", text)  # & survived escaping
        self.assertIn("Risk <high>", text)          # < > did not break the parser

    def test_notes_pdf_handles_empty_and_inline_bold(self):
        self.assertTrue(notes_to_pdf("").startswith(b"%PDF"))
        self.assertTrue(notes_to_pdf("Some **bold** and *odd* <b>tags").startswith(b"%PDF"))

    def test_quiz_pdf_uses_resolved_answer_text(self):
        rows = [{"question": "P/E < 10?", "your_answer": "Yes & no", "correct_answer": "Beta",
                 "explanation": "Because <reasons>"}]
        text = extract_pdf_text(io.BytesIO(quiz_results_to_pdf(rows, 0, 1)))
        self.assertIn("Final Score: 0/1", text)
        self.assertIn("Correct Answer: Beta", text)


if __name__ == "__main__":
    unittest.main()
