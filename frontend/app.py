import hashlib
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st

from app import config
from app.database import db
from app.errors import AppError, AuthError, VoiceError
from app.llm import llm_model
from app.notes.notes_generator import generate_notes
from app.quiz.evaluator import evaluate_answer
from app.quiz.quiz_generator import generate_quiz, is_correct, resolve_correct_option
from app.quiz.tutor_engine import ask_tutor
from app.rag.chatbot import finance_chat
from app.rag.loader import list_source_files, load_documents, load_file
from app.rag.sources import format_sources
from app.rag.vector_store import add_documents, create_vector_store, vector_store_exists
from app.utils.pdf_export import notes_to_pdf, quiz_results_to_pdf
from app.utils.text import fix_math, pdf_bytes_to_text
from app.utils.voice_utils import text_to_speech_bytes, transcribe_audio_bytes

_FAILED = object()

# ------------------------------------------------------------------ constants
HOME, ASK, QUIZ, CHAT, NOTES, KB, PROGRESS = (
    "🏠 Home", "🎓 Ask a Question", "📝 Quiz", "💬 Chatbot",
    "🗒️ Study Notes", "📚 Knowledge Base", "📈 My Progress",
)
FEATURES = [
    (ASK, "Ask a Question", "Get answers grounded in the knowledge base, with sources."),
    (QUIZ, "Take a Quiz", "Auto-generated multiple-choice quizzes with instant feedback."),
    (CHAT, "Chat", "Ask follow-ups, optionally about your own PDF report."),
    (NOTES, "Study Notes", "Exam-ready notes on any topic, exported as PDF."),
    (KB, "Knowledge Base", "Add your own PDF, CSV, TXT or Markdown files."),
    (PROGRESS, "My Progress", "Sign in to track every quiz attempt and your average."),
]
STARTERS = [
    "What does bond duration measure?",
    "What does the Sharpe ratio measure?",
    "How do futures reduce counterparty risk?",
    "What is dollar-cost averaging?",
]
NOTE_TOPICS = ["Bond duration", "CAPM", "DCF valuation", "Options basics"]
STYLES = {
    "Concise": "Answer clearly in 3-4 sentences.",
    "Detailed": "Give a thorough explanation with a worked example.",
    "Beginner-friendly": "Explain for a complete beginner, using an everyday analogy.",
}

CSS = """
<style>
.block-container { padding-top: 2.2rem; max-width: 1100px; }
.hero { padding: 1.5rem 1.8rem; border-radius: 18px; margin-bottom: 1.2rem; color: #fff;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 55%, #0EA5E9 100%); }
.hero h1 { margin: 0; padding: 0; font-size: 1.9rem; color: #fff; }
.hero p { margin: .35rem 0 0; opacity: .92; font-size: 1.02rem; }
.step { display: inline-flex; width: 1.7rem; height: 1.7rem; align-items: center;
        justify-content: center; border-radius: 50%; background: #4F46E5; color: #fff;
        font-weight: 600; font-size: .9rem; margin-right: .5rem; }
.pill { display: inline-block; padding: .12rem .65rem; border-radius: 999px; font-size: .8rem;
        background: rgba(79,70,229,.16); border: 1px solid rgba(79,70,229,.35); }
div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] > button[kind="primary"],
div.stDownloadButton > button { border-radius: 10px; font-weight: 600; }
</style>
"""

# Dark mode: the app is built on a light base theme (see .streamlit/config.toml) and this
# inverts the whole page. The two backgrounds below are chosen so they invert to Streamlit's
# usual dark colours (#0E1117 and #262730). Elements that must keep their colours are
# inverted a second time, which cancels out.
DARK_CSS = """
<style>
html { filter: invert(1) hue-rotate(180deg); }
.stApp { background-color: #F1EEE8 !important; }
[data-testid="stSidebar"] { background-color: #D9D8CF !important; }
.hero, .step { filter: invert(1) hue-rotate(180deg); }
</style>
"""

HIDE_SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
</style>
"""


# ------------------------------------------------------------------ helpers
def hero(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
                unsafe_allow_html=True)


def md(text):
    """Render model text as Markdown with formulas that Streamlit can display."""
    st.markdown(fix_math(text))


def guarded(fn, *args, spinner="Thinking...", **kwargs):
    """Run fn and show friendly messages instead of tracebacks. Returns _FAILED on error."""
    try:
        with st.spinner(spinner):
            return fn(*args, **kwargs)
    except ValueError as exc:
        st.warning(str(exc))
    except AppError as exc:
        st.error(str(exc))
    except Exception as exc:  # last resort: never show a raw traceback to the user
        st.error(f"Something went wrong: {exc}")
    return _FAILED


def render_sources(docs):
    sources = format_sources(docs)
    if not sources:
        st.caption("No matching passages were found in the knowledge base; "
                   "this answer comes from general knowledge.")
        return
    with st.expander(f"📚 Sources ({len(sources)})"):
        for s in sources:
            with st.container(border=True):
                st.markdown(f"**[{s['n']}] {s['source']}**")
                st.caption(s["snippet"])


def make_audio(text):
    try:
        return text_to_speech_bytes(text)
    except VoiceError as exc:
        st.warning(str(exc))
        return None


def voice_input(label, key):
    """Record in the browser, transcribe once per recording. Returns (text, digest)."""
    if not hasattr(st, "audio_input"):
        st.caption("Voice input needs Streamlit 1.39 or newer.")
        return None, None
    audio = st.audio_input(label, key=key)
    if audio is None:
        return None, None
    data = audio.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    cache = st.session_state.setdefault("_voice_cache", {})
    if cache.get(key, (None, None))[0] != digest:
        try:
            with st.spinner("Transcribing..."):
                cache[key] = (digest, transcribe_audio_bytes(data))
        except VoiceError as exc:
            st.warning(str(exc))
            cache[key] = (digest, None)
    return cache[key][1], digest


def read_pdf_upload(uploaded):
    result = guarded(pdf_bytes_to_text, uploaded.getvalue(), spinner="Reading PDF...")
    if result is _FAILED:
        return None
    if not result:
        st.warning("No text could be extracted from this PDF (is it a scanned image?).")
        return None
    return result


# Callbacks (run before the next rerun, so they may set widget state safely)
def go(page):
    st.session_state["page"] = page


def ask_example(question):
    st.session_state.update(page=ASK, ask_q=question, ask_autorun=True)


def chat_example(question):
    st.session_state["pending_chat"] = question


def notes_example(topic):
    st.session_state.update(notes_topic=topic, notes_autorun=True)


def continue_as_guest():
    st.session_state["guest"] = True


def leave_guest():
    st.session_state.pop("guest", None)


def sign_out():
    for key in ("user", "guest", "quiz", "quiz_meta", "quiz_results", "chat_history",
                "report_text", "ask_result", "notes"):
        st.session_state.pop(key, None)


def reset_quiz():
    for key in ("quiz", "quiz_meta", "quiz_results"):
        st.session_state.pop(key, None)


# ------------------------------------------------------------------ theme, auth, sidebar
def theme_toggle(container):
    container.toggle("🌙 Dark mode", key="dark")


def auth_page():
    """Full-page sign in / register screen shown before the app."""
    st.markdown(HIDE_SIDEBAR_CSS, unsafe_allow_html=True)
    _, right = st.columns([5, 1])
    theme_toggle(right)
    hero("Welcome to Finance Tutor",
         "Sign in to save your quiz history and track your progress.")

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        login_tab, register_tab = st.tabs(["Sign in", "Create account"])
        with login_tab, st.form("login_form"):
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            if st.form_submit_button("Sign in", type="primary"):
                found = guarded(db.authenticate, u, p, spinner="Signing in...")
                if found is None:
                    st.error("Wrong username or password.")
                elif found is not _FAILED:
                    st.session_state["user"] = found
                    st.rerun()
        with register_tab, st.form("register_form"):
            u = st.text_input("Choose a username", key="reg_user")
            p = st.text_input("Password (8+ characters)", type="password", key="reg_pass")
            if st.form_submit_button("Create account", type="primary"):
                try:
                    uid = db.create_user(u, p)
                    st.session_state["user"] = {"id": uid, "username": u.strip().lower()}
                    st.rerun()
                except AuthError as exc:
                    st.error(str(exc))
        if not config.login_required():
            st.caption("Just exploring? You can use everything except saved progress.")
            st.button("Continue as guest", on_click=continue_as_guest)


def sidebar_nav(user):
    with st.sidebar:
        st.markdown("### 📊 Finance Tutor")
        choice = st.radio("Navigate", [HOME, ASK, QUIZ, CHAT, NOTES, KB, PROGRESS],
                          key="page", label_visibility="collapsed")
        st.divider()
        if user:
            st.markdown(f"👤 **{user['username']}**")
            st.button("Sign out", on_click=sign_out)
        else:
            st.caption("Browsing as a guest")
            st.button("Sign in / Register", on_click=leave_guest)
        theme_toggle(st)
        st.caption(f"Model: {llm_model.current_model()}")
    return choice


# ------------------------------------------------------------------ pages
def page_home(user):
    hero("Your AI finance tutor",
         "Ask questions grounded in real documents, practise with quizzes, and track your progress.")

    stats = db.get_user_stats(user["id"]) if user else None
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents indexed", len(list_source_files()))
    c2.metric("Quizzes taken", stats["attempts"] if stats else "—")
    c3.metric("Average score", f"{stats['average_pct']}%" if stats and stats["attempts"] else "—")

    st.markdown("#### What would you like to do?")
    for row in range(0, len(FEATURES), 3):
        cols = st.columns(3)
        for col, (page, title, desc) in zip(cols, FEATURES[row:row + 3]):
            with col, st.container(border=True):
                st.markdown(f"**{page.split(' ', 1)[0]} {title}**")
                st.caption(desc)
                st.button("Open", key=f"open_{title}", on_click=go, args=(page,))

    st.markdown("#### Try asking")
    cols = st.columns(2)
    for i, q in enumerate(STARTERS):
        cols[i % 2].button(q, key=f"home_ex_{i}", on_click=ask_example, args=(q,))


def page_ask():
    hero("Ask a finance question", "Answers come from the knowledge base and cite their sources.")

    st.caption("Try an example:")
    cols = st.columns(2)
    for i, q in enumerate(STARTERS):
        cols[i % 2].button(q, key=f"ask_ex_{i}", on_click=ask_example, args=(q,))

    with st.form("ask_form"):
        typed = st.text_input("Your question", key="ask_q",
                              placeholder="e.g. What does bond duration measure?")
        c1, c2 = st.columns([3, 2])
        style_name = c1.selectbox("Answer style", list(STYLES), key="ask_style")
        read_aloud = c2.checkbox("Read the answer aloud", key="ask_tts")
        submitted = st.form_submit_button("Get answer", type="primary")

    with st.expander("🎤 Ask with your voice"):
        voice_text, _ = voice_input("Record your question", key="ask_voice")
        if voice_text:
            st.caption(f"You said: {voice_text}")

    autorun = st.session_state.pop("ask_autorun", False)
    if submitted or autorun:
        question = (typed or "").strip() or (voice_text or "")
        res = guarded(ask_tutor, question, style=STYLES[style_name],
                      spinner="Searching the knowledge base...")
        if res is not _FAILED:
            answer, docs = res
            audio = make_audio(answer) if read_aloud else None
            st.session_state.ask_result = {"q": question, "a": answer, "docs": docs, "audio": audio}

    result = st.session_state.get("ask_result")
    if result:
        with st.container(border=True):
            st.caption(f"Question: {result['q']}")
            st.markdown("#### Answer")
            md(result["a"])
            if result["audio"]:
                st.audio(result["audio"], format="audio/mp3")
        render_sources(result["docs"])


def page_quiz(user):
    hero("Quiz yourself", "Generate a multiple-choice quiz on any topic and get instant feedback.")
    results = st.session_state.get("quiz_results")
    quiz = st.session_state.get("quiz")

    if results:
        show_results(results)
        st.button("Start a new quiz", type="primary", on_click=reset_quiz)
        return
    if not quiz:
        quiz_setup()
        return
    quiz_questions(quiz, user)


def quiz_setup():
    with st.container(border=True):
        st.markdown('<span class="step">1</span> **Choose a topic**', unsafe_allow_html=True)
        topic = st.text_input("Topic", key="quiz_topic",
                              placeholder="e.g. Bonds, Options, Portfolio theory")
        c1, c2 = st.columns(2)
        difficulty = c1.radio("Difficulty", ["easy", "medium", "hard"], horizontal=True,
                              key="quiz_diff")
        num_questions = c2.slider("Number of questions", 3, 15, 5, key="quiz_n")
        with st.expander("📄 Base the quiz on a PDF report (optional)"):
            uploaded = st.file_uploader("PDF report", type=["pdf"], key="quiz_pdf")
            report_text = read_pdf_upload(uploaded) if uploaded else None
            if report_text:
                st.success("Report loaded. Questions will use it as context.")
        if st.button("Generate quiz", type="primary"):
            if not (topic or "").strip():
                st.warning("Please enter a topic first.")
                return
            quiz = guarded(generate_quiz, topic.strip(), report_text, difficulty,
                           num_questions, spinner="Writing your quiz...")
            if quiz is _FAILED:
                return
            if not quiz:
                st.error("The model did not return a usable quiz. Please try again.")
                return
            st.session_state.quiz = quiz
            st.session_state.quiz_meta = {"topic": topic.strip(), "difficulty": difficulty}
            st.session_state.quiz_id = st.session_state.get("quiz_id", 0) + 1
            st.rerun()


def quiz_questions(quiz, user):
    meta, qid = st.session_state.quiz_meta, st.session_state.quiz_id
    answers = [st.session_state.get(f"quiz{qid}_q{i}") for i in range(len(quiz))]
    done = sum(a is not None for a in answers)

    st.markdown(f"**{meta['topic']}**  ·  {meta['difficulty']}  ·  {len(quiz)} questions")
    st.progress(done / len(quiz), text=f"{done} of {len(quiz)} answered")

    for i, q in enumerate(quiz):
        with st.container(border=True):
            st.markdown(fix_math(f"**Q{i + 1}.** {q['question']}"))
            st.radio("Your answer", q["options"], index=None, key=f"quiz{qid}_q{i}",
                     label_visibility="collapsed")

    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("Submit quiz", type="primary"):
        if any(a is None for a in answers):
            st.warning("Please answer every question before submitting.")
        else:
            st.session_state.quiz_results = grade_quiz(quiz, answers, meta, user)
            st.rerun()
    c2.button("Discard", on_click=reset_quiz)


def grade_quiz(quiz, answers, meta, user):
    """Score deterministically, ask the LLM for feedback only on wrong answers (once)."""
    rows, score = [], 0
    with st.spinner("Grading..."):
        for q, a in zip(quiz, answers):
            correct_text = resolve_correct_option(q)
            ok = is_correct(q, a)
            score += ok
            feedback = None
            if not ok:
                try:
                    feedback = evaluate_answer(q["question"], correct_text, a)
                except AppError:
                    feedback = None  # fall back to the stored explanation
            rows.append({"question": q["question"], "your_answer": a,
                         "correct_answer": correct_text, "correct": ok,
                         "explanation": q["explanation"], "feedback": feedback})
    saved = False
    if user:
        try:
            db.save_quiz_attempt(user["id"], meta["topic"], meta["difficulty"],
                                 score, len(quiz), rows)
            saved = True
        except Exception as exc:
            st.warning(f"Could not save this attempt: {exc}")
    return {"rows": rows, "score": score, "total": len(quiz), "saved": saved,
            "topic": meta["topic"], "difficulty": meta["difficulty"],
            "pdf": quiz_results_to_pdf(rows, score, len(quiz))}


def show_results(results):
    score, total = results["score"], results["total"]
    pct = round(100 * score / total)
    if pct >= 80:
        verdict = "🎉 Excellent work!"
    elif pct >= 50:
        verdict = "👍 Good effort. Review the misses below."
    else:
        verdict = "📚 Keep practising. Read the explanations below."

    with st.container(border=True):
        st.markdown(f"### {verdict}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Score", f"{score}/{total}")
        c2.metric("Accuracy", f"{pct}%")
        c3.metric("Level", results["difficulty"].title())
        st.progress(pct / 100)

    for i, r in enumerate(results["rows"], 1):
        with st.expander(f"{'✅' if r['correct'] else '❌'}  Q{i}. {r['question']}",
                         expanded=not r["correct"]):
            st.markdown(f"**Your answer:** {r['your_answer']}")
            st.markdown(f"**Correct answer:** {r['correct_answer']}")
            if r["feedback"]:
                st.info(fix_math(r["feedback"]))
            if r["explanation"]:
                st.caption(fix_math(f"Explanation: {r['explanation']}"))

    if results["saved"]:
        st.caption("✔ Saved to your progress.")
    elif not st.session_state.get("user"):
        st.caption("Sign in from the sidebar to save results to your progress page.")
    st.download_button("⬇ Download results (PDF)", data=results["pdf"],
                       file_name="finance_quiz_results.pdf", mime="application/pdf")


def page_chat():
    hero("Finance chatbot", "Ask follow-up questions, optionally about your own uploaded report.")
    history = st.session_state.setdefault("chat_history", [])

    top = st.columns([4, 1])
    if st.session_state.get("report_text"):
        top[0].markdown('<span class="pill">📄 Report loaded</span>', unsafe_allow_html=True)
    if top[1].button("Clear chat"):
        st.session_state.chat_history = []
        st.session_state.pop("report_text", None)
        st.rerun()

    with st.expander("📄 Chat about a PDF report (optional)"):
        uploaded = st.file_uploader("Finance report", type=["pdf"], key="chat_pdf")
        if uploaded:
            text = read_pdf_upload(uploaded)
            if text:
                st.session_state.report_text = text
                st.success("Report loaded. Ask questions about it below.")

    if not history:
        st.caption("Try asking:")
        cols = st.columns(2)
        for i, q in enumerate(STARTERS):
            cols[i % 2].button(q, key=f"chat_ex_{i}", on_click=chat_example, args=(q,))

    for msg in history:
        with st.chat_message(msg["role"]):
            md(msg["content"])
            if msg["role"] == "assistant" and msg.get("docs") is not None:
                render_sources(msg["docs"])

    with st.expander("🎤 Voice question"):
        voice_text, digest = voice_input("Record a question", key="chat_voice")
        read_aloud = st.checkbox("Read answers aloud", key="chat_tts")

    new_message = st.chat_input("Ask anything about finance...")
    pending = st.session_state.pop("pending_chat", None)
    new_message = new_message or pending
    if voice_text and digest != st.session_state.get("last_voice_digest"):
        st.session_state.last_voice_digest = digest
        new_message = voice_text

    if new_message:
        with st.chat_message("user"):
            st.markdown(new_message)
        res = guarded(finance_chat, new_message,
                      history=[{"role": m["role"], "content": m["content"]} for m in history],
                      report_context=st.session_state.get("report_text"))
        if res is not _FAILED:
            answer, docs = res
            with st.chat_message("assistant"):
                md(answer)
                render_sources(docs)
                if read_aloud:
                    audio = make_audio(answer)
                    if audio:
                        st.audio(audio, format="audio/mp3")
            history.append({"role": "user", "content": new_message})
            history.append({"role": "assistant", "content": answer, "docs": docs})


def page_notes():
    hero("Study notes", "Structured, exam-ready notes on any finance topic, exported as PDF.")

    st.caption("Popular topics:")
    cols = st.columns(len(NOTE_TOPICS))
    for col, t in zip(cols, NOTE_TOPICS):
        col.button(t, key=f"note_ex_{t}", on_click=notes_example, args=(t,))

    with st.form("notes_form"):
        topic = st.text_input("Topic", key="notes_topic", placeholder="e.g. Convexity")
        submitted = st.form_submit_button("Generate notes", type="primary")

    autorun = st.session_state.pop("notes_autorun", False)
    if submitted or autorun:
        notes = guarded(generate_notes, topic, spinner="Writing notes...")
        if notes is not _FAILED:
            st.session_state.notes = notes
            st.session_state.notes_pdf = notes_to_pdf(notes)
            st.session_state.notes_title = topic.strip()

    if st.session_state.get("notes"):
        with st.container(border=True):
            st.markdown(f"#### {st.session_state.get('notes_title', 'Notes')}")
            md(st.session_state.notes)
        st.download_button("⬇ Download as PDF", data=st.session_state.notes_pdf,
                           file_name="finance_notes.pdf", mime="application/pdf")


def page_knowledge_base():
    hero("Knowledge base", "The tutor answers from these documents. Add your own and they are indexed immediately.")
    overview = st.container()

    st.markdown("#### Add documents")
    types = [e.lstrip(".") for e in sorted(config.SUPPORTED_EXTENSIONS)]
    uploads = st.file_uploader("PDF, CSV, TXT or Markdown", type=types, accept_multiple_files=True)
    if uploads and st.button("Add to knowledge base", type="primary"):
        for up in uploads:
            name = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(up.name).name)
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            target = config.DATA_DIR / name
            target.write_bytes(up.getvalue())
            docs = load_file(target)
            if not docs:
                st.warning(f"{name}: no readable text found, skipped.")
                target.unlink(missing_ok=True)
                continue
            n = guarded(add_documents, docs, spinner=f"Indexing {name}...")
            if n is not _FAILED:
                st.success(f"{name}: indexed ({n} chunks).")

    with st.expander("Advanced"):
        if st.button("Rebuild entire index"):
            res = guarded(lambda: create_vector_store(load_documents()), spinner="Rebuilding index...")
            if res is not _FAILED:
                st.success("Index rebuilt.")

    # Filled last so it reflects files added above in the same run
    files = list_source_files()
    with overview:
        c1, c2, c3 = st.columns(3)
        c1.metric("Documents", len(files))
        c2.metric("Total size", f"{sum(f.stat().st_size for f in files) / 1024:.0f} KB")
        c3.metric("Index", "Ready" if vector_store_exists() else "Builds on first question")
        if files:
            st.dataframe([{"File": f.relative_to(config.DATA_DIR).as_posix(),
                           "Type": f.suffix.lstrip(".").upper(),
                           "Size (KB)": round(f.stat().st_size / 1024, 1)} for f in files],
                         hide_index=True)


def page_progress(user):
    hero("My progress", "Your saved quiz attempts and scores.")
    if not user:
        st.info("Sign in from the sidebar to see your saved quiz attempts.")
        return
    stats = db.get_user_stats(user["id"])
    history = db.get_quiz_history(user["id"])
    c1, c2 = st.columns(2)
    c1.metric("Quizzes taken", stats["attempts"])
    c2.metric("Average score", f"{stats['average_pct']}%")
    if not history:
        st.info("No quizzes yet. Take one on the Quiz page!")
        return

    st.markdown("#### Score trend (oldest to newest)")
    st.bar_chart({"Score %": [round(100 * h["score"] / h["total"]) for h in reversed(history)]})

    st.markdown("#### Attempts")
    for h in history:
        label = f"{h['created_at']} UTC  ·  {h['topic']} ({h['difficulty']})  ·  {h['score']}/{h['total']}"
        with st.expander(label):
            for i, r in enumerate(h["details"], 1):
                st.markdown(f"{'✅' if r['correct'] else '❌'} **Q{i}.** {r['question']}")
                st.caption(f"Your answer: {r['your_answer']}  ·  Correct: {r['correct_answer']}")


# ------------------------------------------------------------------ main
def main():
    st.set_page_config(page_title="Finance Tutor Bot", page_icon="📊", layout="wide")
    st.session_state.setdefault("dark", st.query_params.get("theme") == "dark")
    st.session_state.setdefault("page", HOME)
    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state["dark"]:
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.query_params["theme"] = "dark" if st.session_state["dark"] else "light"

    user = st.session_state.get("user")
    guest_ok = st.session_state.get("guest") and not config.login_required()
    if not user and not guest_ok:
        auth_page()
        st.stop()

    choice = sidebar_nav(user)
    pages = {
        HOME: lambda: page_home(user),
        ASK: page_ask,
        QUIZ: lambda: page_quiz(user),
        CHAT: page_chat,
        NOTES: page_notes,
        KB: page_knowledge_base,
        PROGRESS: lambda: page_progress(user),
    }
    pages.get(choice, pages[HOME])()


main()