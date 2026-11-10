import io
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.llm import llm_model as lm
from app.utils.pdf_export import notes_to_pdf
from app.utils.text import extract_pdf_text, fix_math

FORMULAS = (r"| Mac | \(\displaystyle D_{\text{Mac}} = \frac{\sum_{t=1}^{n} t \cdot PV_t}{P}\) | x |" "\n"
            r"| dP | \(\Delta P \approx -D_{\text{Mod}}\Delta y + \frac{1}{2}C(\Delta y)^2\) | y |")


class FixMathTests(unittest.TestCase):
    def test_paren_and_bracket_delimiters_become_dollars(self):
        self.assertEqual(fix_math(r"so \(a+b\) and \[x^2\]"), "so $a+b$ and $$x^2$$")

    def test_multiline_math(self):
        self.assertEqual(fix_math("\\(\na\n+ b\n\\)"), "$a\n+ b$")

    def test_screenshot_formulas_have_no_paren_delimiters_left(self):
        out = fix_math(FORMULAS)
        self.assertNotIn("\\(", out)
        self.assertNotIn("\\)", out)
        self.assertIn(r"$\Delta P \approx", out)

    def test_money_is_escaped_but_math_is_not(self):
        self.assertEqual(fix_math("costs $100 and $2,500.50 total"), r"costs \$100 and \$2,500.50 total")
        self.assertEqual(fix_math("math $2^n$ and $x$"), "math $2^n$ and $x$")

    def test_idempotent_and_empty_safe(self):
        once = fix_math(FORMULAS + " costs $5 million")
        self.assertEqual(fix_math(once), once)
        self.assertEqual(fix_math(None), "")
        self.assertEqual(fix_math(""), "")


class PdfMathTests(unittest.TestCase):
    def pdf_text(self, notes):
        return extract_pdf_text(io.BytesIO(notes_to_pdf(notes)))

    def test_latex_is_readable_not_raw(self):
        text = self.pdf_text(FORMULAS + "\n- Zero coupon: $D_{Mac} = n$\nCosts $100 and $200")
        self.assertIn("Delta", text)
        for raw in ("\\frac", "\\Delta", "\\text", "\\cdot", "\\("):
            self.assertNotIn(raw, text)
        self.assertIn("$100", text)  # money stays untouched

    def test_special_characters_still_safe(self):
        self.assertTrue(notes_to_pdf("a < b & c > d \\(x < y\\)").startswith(b"%PDF"))


class TruncationTests(unittest.TestCase):
    def reply(self, finish_reason):
        llm = MagicMock()
        llm.invoke.return_value = SimpleNamespace(
            content="partial", response_metadata={"finish_reason": finish_reason})
        return llm

    def test_cut_off_answers_are_flagged(self):
        with patch("app.llm.llm_model.get_llm", return_value=self.reply("length")):
            out = lm.invoke_llm("q")
        self.assertTrue(out.startswith("partial"))
        self.assertIn("cut off", out)

    def test_normal_answers_unchanged(self):
        with patch("app.llm.llm_model.get_llm", return_value=self.reply("stop")):
            self.assertEqual(lm.invoke_llm("q"), "partial")


if __name__ == "__main__":
    unittest.main()