# Changelog

## Bug fixes
- **Ask Finance Question / Chatbot crashed**: the UI treated `ask_tutor()`'s `(answer, docs)` tuple as a string (broke the UI and text-to-speech). It now unpacks it correctly and shows sources.
- The UI wrapped the question in a long prompt before retrieval, so the vector search ran on the wrapper text; retrieval now uses the clean question and `report_context` is actually passed through.
- **Retrieval eval crashed** (`questions.jsonl` pointed at a non-existent `bonds.txt`) and the data folder held empty files, so chunk-size variants were identical. Added real seed documents, 16 verified questions, and a test that every key fact exists in its source.
- **Quiz grading re-ran the LLM for every question on every Streamlit rerun.** Scoring is now deterministic and computed once; the LLM only comments on wrong answers.
- Quiz answers like `"Option B"` / `"B)"` are now resolved to the option text; the PDF export previously printed the raw letter.
- PDF export crashed on `&`, `<`, `>` in LLM text; text is now escaped. `PyPDF2.extract_text()` returning `None` no longer crashes uploads.
- "Download Notes" nested a button inside a button; the PDF download is now available right after generation.
- `Finance Chatbot` page ignored `chatbot.py` and conversation history; both are now used.
- Paths were relative to the working directory; all paths are now absolute (`app/config.py`).
- Radio buttons had a silent default answer; quizzes now start unanswered and require every answer.

## Limitations & roadmap items addressed
See the README: complete `requirements.txt`, bundled seed data with auto-built index, cloud-compatible voice, tests + CI, error handling, Docker, deployment config, source citations, PDF/CSV ingestion, authentication and quiz history.

## Compatibility
- Uses `langchain-chroma` / `langchain-huggingface` (LangChain 1.x) with an automatic fallback to `langchain-community` (`app/rag/compat.py`).
- `requirements.txt` rewritten for the LangChain 1.x family; Flask-era packages (Flask, Jinja2, matplotlib, scikit-learn, jupyter, ...) dropped.
