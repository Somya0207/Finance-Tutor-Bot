# 📊 Finance Tutor Bot

An AI-powered finance learning assistant that combines **Retrieval-Augmented Generation (RAG)**, **quiz generation**, **study notes generation**, and **voice interaction** in a single Streamlit app — built to help students and self-learners understand finance concepts, test their knowledge, and get personalized feedback.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎓 **Ask Finance Question** | Ask any finance question by typing or speaking. Answers are grounded in a document knowledge base using RAG, and can be read back aloud. |
| 📝 **Generate Quiz** | Auto-generates multiple-choice quizzes on any finance topic (optionally grounded in an uploaded investment report PDF), with adjustable difficulty and question count. Answers are graded by an LLM evaluator, and results can be exported as a PDF. |
| 💬 **Finance Chatbot** | A conversational chatbot that can answer follow-up questions about an uploaded finance report, with full chat history and voice input/output. |
| 🗒️ **Study Notes** | Generates structured, exam-ready study notes on any finance topic and exports them as a formatted PDF. |

---

## 🧠 How It Works

The project is built around a **RAG (Retrieval-Augmented Generation) pipeline**:

1. Finance documents (`.txt` files) are loaded and split into chunks.
2. Each chunk is converted into a vector embedding using a HuggingFace sentence-transformer model.
3. Embeddings are stored in a **Chroma** vector database.
4. When a user asks a question, the most relevant chunks are retrieved from Chroma and passed to an **LLM (Llama 3.1 8B via Groq)** as context.
5. The LLM generates a grounded, context-aware answer.

```
User Question
     │
     ▼
Retriever (Chroma vector DB)
     │  fetches relevant document chunks
     ▼
LLM (Groq / Llama 3.1 8B)
     │  generates answer using retrieved context
     ▼
Streamlit UI  →  (optional) Text-to-Speech
```

---

## 🗂️ Project Structure

```
Finance-Tutor-Bot/
├── main.py                      # Simple CLI demo (standalone evaluator test)
├── build_db.py                  # One-time script to build the Chroma vector database
├── requirements.txt             # Python dependencies
│
├── app/
│   ├── llm/
│   │   └── llm_model.py         # Groq LLM client configuration
│   │
│   ├── rag/
│   │   ├── loader.py            # Loads .txt documents from disk
│   │   ├── embedding.py         # Sentence-transformer embedding model
│   │   ├── vector_store.py      # Builds/persists the Chroma vector store
│   │   ├── retriever.py         # Wraps Chroma as a retriever
│   │   └── chatbot.py           # RAG-based chatbot logic
│   │
│   ├── quiz/
│   │   ├── quiz_generator.py    # Generates MCQ quizzes as structured JSON
│   │   ├── evaluator.py         # Grades a student's free-text answer
│   │   └── tutor_engine.py      # RAG-based "ask a tutor" Q&A logic
│   │
│   ├── notes/
│   │   └── notes_generator.py   # Generates structured study notes
│   │
│   └── utils/
│       └── voice_utils.py       # Speech-to-text and text-to-speech helpers
│
└── frontend/
    └── app.py                   # Streamlit UI — wires all features together
```

> 📄 **New to this codebase?** See [`PROJECT_EXPLAINED.pdf`](./PROJECT_EXPLAINED.pdf) for a beginner-friendly, file-by-file walkthrough of every concept used in this project.

---

## 🛠️ Tech Stack

- **LLM:** Groq API — Llama 3.1 8B Instant (via `langchain-groq`)
- **RAG Orchestration:** LangChain
- **Vector Database:** Chroma
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace, CPU)
- **Frontend:** Streamlit
- **PDF Handling:** PyPDF2 (read), ReportLab (generate)
- **Voice:** SpeechRecognition (speech-to-text), gTTS (text-to-speech)

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Somya0207/Finance-Tutor-Bot.git
cd Finance-Tutor-Bot
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
> ⚠️ **Note:** `requirements.txt` currently only lists transitive/sub-dependencies. Make sure the following top-level packages are also installed, as they're imported directly in the code but missing from the file:
> ```
> streamlit
> langchain-groq
> langchain-community
> PyPDF2
> reportlab
> SpeechRecognition
> gTTS
> python-dotenv
> ```

### 4. Set up environment variables
Create a `.env` file in the project root:
```
GROQ_API=your_groq_api_key_here
```
Get a free API key at [console.groq.com](https://console.groq.com).

### 5. Add source documents
Create a folder `data/investment_reports/` in the project root and add `.txt` files containing finance knowledge (articles, notes, reports, etc.) that the RAG system will retrieve from.

### 6. Build the vector database
```bash
python build_db.py
```
This creates a `vector_db/` folder containing the Chroma index.

### 7. Run the app
```bash
streamlit run frontend/app.py
```

---

## 📸 Screenshots

*(Add screenshots or a short demo GIF of the app here — this significantly boosts recruiter engagement on GitHub/resumes.)*

---

## 🚧 Known Limitations

- `requirements.txt` is incomplete (see setup note above).
- `data/investment_reports/` and `vector_db/` are not included in the repo (gitignored) — the app won't run out-of-the-box without seed data.
- Voice features (`speech_recognition`) require a local microphone and internet access to Google's recognition API — this won't work on cloud deployments like Streamlit Community Cloud without modification.
- No automated tests currently exist.
- API keys and errors (e.g. failed LLM calls, empty retriever) are not gracefully handled in the UI.

---

## 🗺️ Roadmap

- [ ] Add unit tests (`pytest`) for `evaluator.py`, `quiz_generator.py`, and the RAG pipeline
- [ ] Add proper error handling and empty-state UI messages
- [ ] Dockerize the app for one-command setup
- [ ] Deploy a live demo
- [ ] Add source-citation to RAG answers (show which document/chunk was used)
- [ ] Support PDF/CSV ingestion directly into the knowledge base, not just `.txt`
- [ ] Add user authentication and quiz history persistence (e.g. SQLite)

---

## 📄 License

This project is currently unlicensed. Consider adding an [MIT License](https://choosealicense.com/licenses/mit/) if you intend to share it publicly.

---

## 👤 Author

**Somya**
GitHub: [@Somya0207](https://github.com/Somya0207)
