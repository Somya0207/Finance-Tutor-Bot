"""PDF export for study notes and quiz results (returns bytes)."""
import io
import re
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

_ROMAN = ("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.", "X.")


# Standard PDF fonts only cover Latin-1, so Greek letters and math symbols become words.
_TEX_WORDS = {
    "cdot": "·", "times": "×", "pm": "±", "Delta": "Delta ", "delta": "delta ",
    "sigma": "sigma", "Sigma": "Sigma", "mu": "mu", "alpha": "alpha", "beta": "beta",
    "lambda": "lambda", "rho": "rho", "theta": "theta", "pi": "pi", "sum": "sum",
    "prod": "prod", "approx": "~", "leq": "&lt;=", "geq": "&gt;=", "neq": "!=",
    "infty": "inf", "to": "-&gt;", "rightarrow": "-&gt;", "ldots": "...",
    "left": "", "right": "", "displaystyle": "", "quad": "  ",
}
_MATH_SPAN = re.compile(
    r"\\\((.+?)\\\)|\\\[(.+?)\\\]|\$\$(.+?)\$\$|(?<!\\)\$([^$\n]*[\\_^={][^$\n]*)\$",
    re.DOTALL,
)


def _tex_to_markup(expr: str) -> str:
    """Turn a LaTeX formula into readable text with ReportLab <sub>/<super> tags."""
    expr = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname)\{([^{}]*)\}", r"\1", expr)
    expr = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", expr)
    expr = re.sub(r"\^\{([^{}]*)\}", r"<super>\1</super>", expr)
    for _ in range(4):  # nested fractions
        expr = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", expr)
    expr = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", expr)
    expr = re.sub(r"\\([A-Za-z]+)", lambda m: _TEX_WORDS.get(m.group(1), m.group(1)), expr)
    expr = re.sub(r"\\[,;:! ]", " ", expr)
    expr = re.sub(r"_([A-Za-z0-9])", r"<sub>\1</sub>", expr)
    expr = re.sub(r"\^([A-Za-z0-9])", r"<super>\1</super>", expr)
    return expr.replace("{", "").replace("}", "")


def _inline(text: str) -> str:
    """Escape XML special chars (LLM text often has & or <), render LaTeX readably,
    then turn **x** into bold."""
    text = escape(text)
    text = _MATH_SPAN.sub(
        lambda m: _tex_to_markup(next(g for g in m.groups() if g is not None)), text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

def _doc(buffer):
    return SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40,
                             topMargin=40, bottomMargin=40)


def notes_to_pdf(notes: str, title="Finance Study Notes") -> bytes:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("NTitle", parent=styles["Title"], alignment=1, spaceAfter=20)
    heading = ParagraphStyle("NHeading", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
    text = ParagraphStyle("NText", parent=styles["Normal"], leftIndent=10, spaceAfter=5, leading=14)
    bullet = ParagraphStyle("NBullet", parent=styles["Normal"], leftIndent=25, spaceAfter=4, leading=14)

    story = [Paragraph(escape(title), title_style), Spacer(1, 15)]
    for raw in (notes or "").split("\n"):
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 8))
        elif line.startswith("#"):
            story.append(Paragraph(f"<b>{_inline(line.lstrip('#').strip())}</b>", heading))
        elif line.startswith(_ROMAN):
            story.append(Paragraph(f"<b>{_inline(line)}</b>", heading))
        elif line.startswith("**") and line.endswith("**") and len(line) > 4:
            story.append(Paragraph(f"<b>{_inline(line.strip('*'))}</b>", heading))
        elif line[:2] in ("- ", "* ", "• "):
            story.append(Paragraph("• " + _inline(line[2:]), bullet))
        else:
            story.append(Paragraph(_inline(line), text))

    buf = io.BytesIO()
    _doc(buf).build(story)
    return buf.getvalue()


def quiz_results_to_pdf(results, score, total, title="Finance Quiz Results") -> bytes:
    """results: list of dicts with question, your_answer, correct_answer, explanation."""
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 20),
             Paragraph(f"Final Score: {score}/{total}", styles["Heading2"]), Spacer(1, 20)]
    for i, r in enumerate(results, 1):
        story += [
            Paragraph(f"Question {i}: {_inline(r['question'])}", styles["Heading3"]),
            Spacer(1, 5),
            Paragraph(f"Your Answer: {_inline(r['your_answer'])}", styles["Normal"]),
            Paragraph(f"Correct Answer: {_inline(r['correct_answer'])}", styles["Normal"]),
            Paragraph(f"Explanation: {_inline(r.get('explanation', ''))}", styles["Normal"]),
            Spacer(1, 15),
        ]
    buf = io.BytesIO()
    _doc(buf).build(story)
    return buf.getvalue()
