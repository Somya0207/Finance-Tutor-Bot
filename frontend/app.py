import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import PyPDF2
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from app.utils.voice_utils import speech_to_text, text_to_speech

from app.quiz.tutor_engine import ask_tutor
from app.quiz.quiz_generator import generate_quiz
from app.quiz.evaluator import evaluate_answer
from app.notes.notes_generator import generate_notes



# SESSION STATE


if "quiz" not in st.session_state:
    st.session_state.quiz = []

if "user_answers" not in st.session_state:
    st.session_state.user_answers = []

if "submitted" not in st.session_state:
    st.session_state.submitted = False



# PAGE CONFIG


st.set_page_config(
    page_title="Finance Tutor Bot ",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Finance Tutor Bot ")

menu = st.sidebar.selectbox(
    "Select Feature",
    [
        "Ask Finance Question",
        "Generate Quiz",
        "Finance Chatbot",
        "Study Notes"
    ]
)

# ASK FINANCE QUESTION


if menu == "Ask Finance Question":

    st.header("Ask Finance Question")

    # Initialize session state
    if "question" not in st.session_state:
        st.session_state.question = ""

    # Text input
    text_input = st.text_input("Enter your finance question")

    #  Voice input
    if st.button("🎤 Speak Question"):
        voice_text = speech_to_text()
        st.session_state.question = voice_text
        st.write("You said:", voice_text)

    # Prefer typed input if given
    if text_input:
        st.session_state.question = text_input

    st.divider()

    #  Single button for answer
    if st.button("Get Answer") and st.session_state.question:

        answer = ask_tutor(f"""
        You are a finance tutor.

        Answer clearly in 3-4 sentences.

        Question: {st.session_state.question}
        """)

        answer_text = answer.content if hasattr(answer, "content") else answer

        st.subheader("AI Tutor Answer")
        st.write(answer_text)

        #  Voice output
        audio_file = text_to_speech(answer_text)

        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        st.audio(audio_bytes, format="audio/mp3")

# GENERATE QUIZ

elif menu == "Generate Quiz":

    st.header("Generate Finance Quiz")

    uploaded_report = st.file_uploader(
        "Upload Investment Report (PDF)",
        type=["pdf"]
    )

    report_text = None

    if uploaded_report is not None:

        pdf_reader = PyPDF2.PdfReader(uploaded_report)

        report_text = ""

        for page in pdf_reader.pages:
            report_text += page.extract_text()

        st.success("Investment Report Uploaded Successfully")

    # 🔹 Topic input
    topic = st.text_input("Enter Topic")

    # ✅ PRO UI (Columns Layout)
    col1, col2 = st.columns(2)

    with col1:
        difficulty = st.radio(
            "Select Difficulty",
            ["easy", "medium", "hard"],
            horizontal=True
        )

    with col2:
        num_questions = st.slider(
            "Number of Questions",
            3,
            15,
            5
        )

    # 🔘 Generate Quiz
    if st.button("Generate Quiz"):

        if not topic:
            st.warning("Please enter a topic first.")
            st.stop()

        # ✅ SAVE USER INPUT
        st.session_state.difficulty = difficulty
        st.session_state.num_questions = num_questions

        quiz_data = generate_quiz(
            topic,
            report_text,
            difficulty,
            num_questions
        )

        if not quiz_data:
            st.error("Quiz could not be generated.")
        else:
            st.session_state.quiz = quiz_data
            st.session_state.submitted = False
            st.success("Quiz generated successfully!")

    # =============================
    # SHOW QUIZ
    # =============================

    if st.session_state.get("quiz"):

        # ✅ SHOW USER SELECTION (SAFE)
        st.info(f"""
📊 Difficulty: {st.session_state.difficulty.upper()}  
📝 Questions: {st.session_state.num_questions}
""")

        st.subheader("Generated Quiz")

        user_answers = []

        for i, q in enumerate(st.session_state.quiz):

            st.write(f"### Question {i+1}")
            st.write(q["question"])

            answer = st.radio(
                "Select your answer:",
                q["options"],
                key=f"q{i}"
            )

            user_answers.append(answer)

        if st.button("Submit Quiz"):
            st.session_state.submitted = True
            st.session_state.user_answers = user_answers

    # =============================
    # SHOW RESULTS
    # =============================

    if st.session_state.get("submitted"):

        score = 0

        st.header("Quiz Results")

        for i, q in enumerate(st.session_state.quiz):

            user = st.session_state.user_answers[i]
            correct = q["answer"]

            if correct in ["A", "B", "C", "D"]:
                correct_index = ord(correct) - ord("A")
                correct_text = q["options"][correct_index]
            else:
                correct_text = correct

            evaluation = evaluate_answer(
                q["question"],
                correct_text,
                user
            )

            if user.strip().lower() == correct_text.strip().lower():
                score += 1
                st.markdown(f"### Question {i+1} 🟢 Correct")
            else:
                st.markdown(f"### Question {i+1} 🔴 Incorrect")

            st.write("Your Answer:", user)
            st.write("Correct Answer:", correct_text)
            st.write("AI Evaluation:", evaluation)
            st.write("Explanation:", q["explanation"])

            st.divider()

        st.success(f"Final Score: {score}/{len(st.session_state.quiz)}")

        # =============================
        # PDF EXPORT
        # =============================

        buffer = io.BytesIO()
        styles = getSampleStyleSheet()

        pdf = SimpleDocTemplate(buffer)
        story = []

        story.append(Paragraph("Finance Quiz Results", styles["Title"]))
        story.append(Spacer(1, 20))

        story.append(
            Paragraph(
                f"Final Score: {score}/{len(st.session_state.quiz)}",
                styles["Heading2"]
            )
        )

        story.append(Spacer(1, 20))

        for i, q in enumerate(st.session_state.quiz):

            story.append(
                Paragraph(
                    f"Question {i+1}: {q['question']}",
                    styles["Heading3"]
                )
            )

            story.append(Spacer(1, 5))

            story.append(
                Paragraph(
                    f"Your Answer: {st.session_state.user_answers[i]}",
                    styles["Normal"]
                )
            )

            story.append(
                Paragraph(
                    f"Correct Answer: {q['answer']}",
                    styles["Normal"]
                )
            )

            story.append(
                Paragraph(
                    f"Explanation: {q['explanation']}",
                    styles["Normal"]
                )
            )

            story.append(Spacer(1, 15))

        pdf.build(story)

        buffer.seek(0)

        st.download_button(
            "Download Quiz Results as PDF",
            data=buffer,
            file_name="finance_quiz_results.pdf",
            mime="application/pdf"
        )
# FINANCE CHATBOT


elif menu == "Finance Chatbot":

    st.header("💬 Finance Chatbot")

    uploaded_report = st.file_uploader(
        "Upload Finance Report (PDF)",
        type=["pdf"]
    )

    if uploaded_report is not None:

        pdf_reader = PyPDF2.PdfReader(uploaded_report)

        report_text = ""

        for page in pdf_reader.pages:
            report_text += page.extract_text()

        st.session_state.report_text = report_text

        st.success("Finance Report Uploaded Successfully")

    #  Voice section ONLY here
    st.subheader("🎤 Voice Question")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    #  Voice Chat Button
    if st.button("Start Voice Chat"):

        voice_text = speech_to_text()

        if voice_text:
            st.session_state.chat_history.append(
                {"role": "user", "content": voice_text}
            )

            with st.chat_message("user"):
                st.markdown(voice_text)

            report_context = st.session_state.get("report_text", "")
            report_context = report_context[:3000]

            prompt = f"""
            Finance Report Content:
            {report_context}

            Question:
            {voice_text}
            """

            response = ask_tutor(prompt)
            response_text = response.content if hasattr(response, "content") else response

            with st.chat_message("assistant"):
                st.markdown(response_text)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": response_text}
            )

            #  Voice response
            audio_response = text_to_speech(response_text)

            with open(audio_response, "rb") as f:
                audio_bytes = f.read()

            st.audio(audio_bytes, format="audio/mp3")

    #  Clear chat
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

    #  Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    #  Text chat input
    user_input = st.chat_input("Ask anything about finance...")

    if user_input:

        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        report_context = st.session_state.get("report_text", "")
        report_context = report_context[:3000]

        prompt = f"""
        Finance Report Content:
        {report_context}

        Question:
        {user_input}
        """

        response = ask_tutor(prompt)
        response_text = response.content if hasattr(response, "content") else response

        with st.chat_message("assistant"):
            st.markdown(response_text)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": response_text}
        )

# STUDY NOTES


elif menu == "Study Notes":

    st.header("Finance Study Notes")

    topic = st.text_input("Enter topic")

    if st.button("Generate Notes"):

        notes = generate_notes(topic)

        st.subheader("Generated Notes")
        st.write(notes)

        st.session_state.notes = notes

    if "notes" in st.session_state:

        if st.button("Download Notes"):

            buffer = io.BytesIO()

            styles = getSampleStyleSheet()

            # ---------- STYLES ----------

            title_style = ParagraphStyle(
                "Title",
                parent=styles["Title"],
                alignment=1,
                spaceAfter=20
            )

            heading_style = ParagraphStyle(
                "Heading",
                parent=styles["Heading2"],
                spaceBefore=12,
                spaceAfter=6
            )

            text_style = ParagraphStyle(
                "Text",
                parent=styles["Normal"],
                leftIndent=10,
                spaceAfter=5,
                leading=14
            )

            bullet_style = ParagraphStyle(
                "Bullet",
                parent=styles["Normal"],
                leftIndent=25,
                spaceAfter=4,
                leading=14
            )

            pdf = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            story = []

            # ---------- TITLE ----------
            story.append(Paragraph("Finance Study Notes", title_style))
            story.append(Spacer(1,15))

            lines = st.session_state.notes.split("\n")

            # ---------- FORMAT LOGIC ----------
            for line in lines:

                line = line.strip()

                if not line:
                    story.append(Spacer(1,8))

                # 🔹 MAIN HEADINGS (I, II, III...)
                elif line.startswith(("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.")):
                    story.append(Spacer(1,10))
                    story.append(Paragraph(f"<b>{line}</b>", heading_style))

                # 🔹 BOLD HEADINGS (**text**)
                elif line.startswith("**") and line.endswith("**"):
                    text = line.replace("**", "")
                    story.append(Paragraph(f"<b>{text}</b>", heading_style))

                # 🔹 NUMBERED LIST (1. 2. 3.)
                elif len(line) > 2 and line[0].isdigit() and "." in line:
                    story.append(Paragraph(line, text_style))

                # 🔹 DASH BULLETS (-)
                elif line.startswith("-"):
                    bullet = line.replace("-", "•", 1)
                    story.append(Paragraph(bullet, bullet_style))

                # 🔹 STAR BULLETS (*)
                elif line.startswith("*"):
                    bullet = "• " + line.replace("*","",1)
                    story.append(Paragraph(bullet, bullet_style))

                # 🔹 NORMAL TEXT
                else:
                    story.append(Paragraph(line, text_style))

            # ---------- BUILD PDF ----------
            pdf.build(story)

            buffer.seek(0)

            st.download_button(
                "Download PDF",
                data=buffer,
                file_name="finance_notes.pdf",
                mime="application/pdf"
            )