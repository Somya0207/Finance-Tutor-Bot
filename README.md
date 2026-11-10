# 📊 Finance Tutor Bot

An AI-powered finance learning assistant that combines **Retrieval-Augmented Generation (RAG)**, **quiz generation**, **study notes**, **voice interaction**, and **user accounts with saved quiz history** in a single Streamlit app — built to help students and self-learners understand finance concepts, test their knowledge, and track their progress.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎓 **Ask Finance Question** | Ask by typing or speaking. Answers are grounded in the knowledge base via RAG, **show the sources they used**, and can be read aloud. |
| 📝 **Generate Quiz** | Auto-generates multiple-choice quizzes on any topic (optionally grounded in an uploaded PDF report) with adjustable difficulty and length. Scoring is deterministic; the LLM gives feedback on the questions you got wrong. Results export to PDF. |
| 💬 **Finance Chatbot** | Conversational follow-ups with chat history, optional uploaded report, voice input/output and source citations. |
| 🗒️ **Study Notes** | Structured, exam-ready notes on any topic, exported as a formatted PDF. |
| 📚 **Knowledge Base** | Upload `.pdf`, `.csv`, `.txt` or `.md` files and they are indexed immediately. |
| 📈 **My Quiz History** | Register / sign in to save every quiz attempt and see your average score. Guests can use everything else. |

---

## 🧠 How It Works

1. Documents (`.txt`, `.md`, `.pdf`, `.csv`) are loaded and split into chunks.
2. Each chunk is embedded with a HuggingFace sentence-transformer and stored in **Chroma**.
3. A question retrieves the most relevant chunks, which are passed to **Llama 3.1 8B (via Groq)** together with the question, optional report excerpts and recent chat history.
4. The answer is shown with numbered **source citations** (file + snippet).
5. The index is **built automatically on first run** from `data/investment_reports/`, so the app works out of the box.

```
Question ─► Retriever (Chroma) ─► top-k chunks ─► LLM (Groq / Llama 3.1 8B) ─► Answer + sources ─► (optional) text-to-speech
```

---

## 🗂️ Project Structure

```
Finance-Tutor-Bot/
├── main.py                      # CLI demo of the answer evaluator
├── build_db.py                  # Rebuild the vector index manually
├── requirements.txt             # Complete top-level dependencies
├── requirements-dev.txt         # + pytest
├── Dockerfile / docker-compose.yml
├── pytest.ini
│
├── app/
│   ├── config.py                # Absolute paths, model + retrieval settings, API-key lookup
│   ├── errors.py                # User-friendly error types shown by the UI
│   ├── llm/llm_model.py         # Lazy Groq client + invoke_llm() with error wrapping
│   ├── rag/
│   │   ├── loader.py            # .txt/.md/.pdf/.csv loading
│   │   ├── embedding.py         # Cached sentence-transformer model
│   │   ├── vector_store.py      # Build / incrementally update / auto-build the Chroma index
│   │   ├── retriever.py         # Chroma retriever
│   │   ├── sources.py           # Builds citation data for the UI
│   │   └── chatbot.py           # Conversational wrapper around the tutor
│   ├── quiz/
│   │   ├── quiz_generator.py    # Robust JSON parsing, validation, answer resolution
│   │   ├── evaluator.py         # LLM feedback on an answer
│   │   └── tutor_engine.py      # RAG Q&A (returns answer + retrieved docs)
│   ├── notes/notes_generator.py
│   ├── database/db.py           # SQLite: users (PBKDF2) + quiz history
│   └── utils/
│       ├── voice_utils.py       # Browser-recorded audio → text, text → speech
│       ├── pdf_export.py        # Notes / quiz-result PDFs (escapes LLM text safely)
│       └── text.py              # PDF text extraction
│
├── data/investment_reports/     # Seed knowledge base (bonds, valuation, portfolio theory, ...)
├── eval/                        # Retrieval evaluation (hit@k, MRR) across chunking strategies
├── tests/                       # Unit + pipeline tests
├── frontend/app.py              # Streamlit UI
└── .github/workflows/tests.yml  # CI
```

> 📄 [`PROJECT_EXPLAINED.pdf`](./PROJECT_EXPLAINED.pdf) is a beginner walkthrough written for the original version of the project; the file layout above is the current one.

---

## 🛠️ Tech Stack

- **LLM:** Groq — Llama 3.1 8B Instant (`langchain-groq`; override with `FTB_MODEL`)
- **RAG:** LangChain 1.x (`langchain-chroma`, `langchain-huggingface`; falls back to `langchain-community` if that's what you have) + Chroma, embeddings `sentence-transformers/all-MiniLM-L6-v2` (CPU)
- **Frontend:** Streamlit (≥ 1.39)
- **Persistence:** SQLite (users, quiz history)
- **PDF:** pypdf (read), ReportLab (write)
- **Voice:** SpeechRecognition + browser recording (speech-to-text), gTTS (text-to-speech)

---

## ⚙️ Setup & Installation

```bash
git clone https://github.com/Somya0207/Finance-Tutor-Bot.git
cd Finance-Tutor-Bot
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # tip: create a fresh venv; old Flask-era packages are not needed
cp .env.example .env              # then put your key in .env  (free key: console.groq.com)
streamlit run frontend/app.py
```

That's it — the seed documents ship with the repo and the vector index is built on the first question (the first run also downloads the embedding model, ~90 MB). To rebuild the index manually: `python build_db.py`.

> **Windows tip:** don't create a lock file with `pip freeze > requirements.txt` in PowerShell — it saves UTF-16. Use `pip freeze | Out-File -Encoding utf8 requirements-lock.txt` (or run it from Command Prompt / Git Bash).

### Add your own knowledge

Use the **Knowledge Base** page in the app, or drop `.txt`, `.md`, `.pdf` or `.csv` files into `data/investment_reports/` and run `python build_db.py`. CSV rows are turned into readable `column: value` lines.

### Accounts

Register from the sidebar to save quiz history. Set `REQUIRE_LOGIN=1` to require sign-in for the whole app. Passwords are stored as salted PBKDF2-SHA256 hashes in a local SQLite file (`app_data/finance_tutor.db`).

---

## 🐳 Docker

```bash
cp .env.example .env              # add GROQ_API
docker compose up --build         # open http://localhost:8501
```

Documents, the vector index and the SQLite database live in named volumes, so they survive restarts.

---

## ☁️ Deploy a live demo (Streamlit Community Cloud)

1. Push the repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io) create an app: repository = yours, **main file = `frontend/app.py`**.
3. In **Advanced settings → Secrets** add `GROQ_API = "your_key"` (see `.streamlit/secrets.toml.example`).
4. Deploy, then put the URL here: **Live demo: _<add your URL>_**

Notes: the free tier has limited memory (the embedding model needs a few hundred MB) and an **ephemeral disk** — accounts, quiz history and uploaded documents reset when the app restarts or redeploys. For persistence use Docker with volumes or a hosted database.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Covers quiz parsing/validation/answer resolution, the RAG prompt and citation logic, LLM error handling, loaders (txt/md/csv/pdf), PDF export (including special characters), the SQLite auth/history layer, the eval scoring, and that every eval question is answerable from the seed data. The Chroma pipeline tests use a fake embedding model (no downloads) and are skipped automatically if `chromadb` isn't installed. CI runs everything via GitHub Actions.

### Retrieval evaluation

Compare chunking strategies on 16 questions with known answers:

```bash
python -m eval.build_variants     # builds vector_db_none / _500 / _1000
python -m eval.retrieval_eval     # prints hit@4, MRR and average context size per variant
```

---

## 🚧 Known Limitations

- **Voice** uses Google's free web speech API (via `SpeechRecognition`) and gTTS, so both need internet access and have no SLA. Recording happens in the browser (works on cloud deployments) but needs Streamlit ≥ 1.39 and microphone permission (HTTPS or localhost).
- The **seed knowledge base is small** (seven short documents). For topics outside it the tutor says so and falls back to the LLM's general knowledge, which can be wrong — check the Sources panel.
- **LLM-generated quizzes and feedback can contain mistakes**; scoring itself is deterministic.
- **Authentication is deliberately basic**: no password reset, email verification or rate limiting, and SQLite is single-node. Don't use it for sensitive data.
- The **knowledge base is shared** by everyone using an instance (no per-user documents).
- On Streamlit Community Cloud, storage is ephemeral (see above).

---

## 🗺️ Roadmap

- [x] Unit tests (`pytest`) for the evaluator, quiz generator, RAG pipeline and more
- [x] Error handling and empty-state messages in the UI
- [x] Dockerized (`Dockerfile`, `docker-compose.yml`)
- [x] Deployment config for a live demo (add your URL once deployed)
- [x] Source citations on RAG answers
- [x] PDF / CSV (and Markdown) ingestion into the knowledge base
- [x] User authentication and quiz-history persistence (SQLite)
- [ ] Password reset / OAuth sign-in
- [ ] Per-user knowledge bases
- [ ] Hybrid search + reranking, streaming answers
- [ ] Postgres option for multi-instance deployments

---

## 📄 License

This project is currently unlicensed. Consider adding an [MIT License](https://choosealicense.com/licenses/mit/) if you intend to share it publicly.

---

## 👤 Author

**Somya**
GitHub: [@Somya0207](https://github.com/Somya0207)
