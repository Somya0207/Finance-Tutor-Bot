import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.errors import KnowledgeBaseEmpty, LLMConfigError
from app.quiz import tutor_engine
from app.rag.sources import format_sources


def doc(text, source="bonds.txt"):
    return SimpleNamespace(page_content=text, metadata={"source": source})


class FakeRetriever:
    def __init__(self, docs):
        self.docs, self.queries = docs, []

    def invoke(self, q):
        self.queries.append(q)
        return self.docs


class AskTutorTests(unittest.TestCase):
    def run_ask(self, question="  What is duration?  ", docs=None, **kw):
        retriever = FakeRetriever(docs if docs is not None else [doc("Duration measures sensitivity.")])
        with patch("app.quiz.tutor_engine.ensure_vector_db") as ensure, \
             patch("app.quiz.tutor_engine.get_retriever", return_value=retriever), \
             patch("app.llm.llm_model.invoke_llm", return_value="ANSWER") as llm:
            result = tutor_engine.ask_tutor(question, **kw)
        return result, retriever, llm, ensure

    def test_returns_text_and_docs_tuple(self):
        (answer, docs), *_ = self.run_ask()
        self.assertEqual(answer, "ANSWER")
        self.assertEqual(len(docs), 1)

    def test_retrieval_uses_clean_stripped_question_only(self):
        _, retriever, _, _ = self.run_ask(report_context="REPORT", style="Be brief.")
        self.assertEqual(retriever.queries, ["What is duration?"])

    def test_prompt_has_context_sources_report_style_and_history(self):
        history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
        _, _, llm, _ = self.run_ask(report_context="Q3 REPORT TEXT", style="Be brief.", history=history)
        prompt = llm.call_args[0][0]
        for expected in ["[1] (source: bonds.txt)", "Duration measures", "Q3 REPORT TEXT",
                         "Be brief.", "Student: hi", "Tutor: hello", "What is duration?"]:
            self.assertIn(expected, prompt)

    def test_report_context_is_truncated(self):
        _, _, llm, _ = self.run_ask(report_context="Z" * 10000)
        self.assertLessEqual(llm.call_args[0][0].count("Z"), 3000)

    def test_no_docs_still_answers(self):
        (answer, docs), _, llm, _ = self.run_ask(docs=[])
        self.assertEqual(docs, [])
        self.assertIn("no matching passages", llm.call_args[0][0])

    def test_empty_question_rejected_before_any_work(self):
        with patch("app.quiz.tutor_engine.ensure_vector_db") as ensure:
            for bad in ["", "   ", None]:
                with self.assertRaises(ValueError):
                    tutor_engine.ask_tutor(bad)
            ensure.assert_not_called()

    def test_empty_knowledge_base_error_propagates(self):
        with patch("app.quiz.tutor_engine.ensure_vector_db", side_effect=KnowledgeBaseEmpty("empty")):
            with self.assertRaises(KnowledgeBaseEmpty):
                tutor_engine.ask_tutor("q")

    def test_missing_api_key_error_propagates(self):
        with patch("app.quiz.tutor_engine.ensure_vector_db"), \
             patch("app.quiz.tutor_engine.get_retriever", return_value=FakeRetriever([])), \
             patch("app.llm.llm_model.get_llm", side_effect=LLMConfigError("no key")):
            with self.assertRaises(LLMConfigError):
                tutor_engine.ask_tutor("q")


class SourcesTests(unittest.TestCase):
    def test_format_sources(self):
        out = format_sources([doc("a   b\nc", "x.txt"), doc("L" * 500, "y.pdf")], snippet_chars=50)
        self.assertEqual(out[0], {"n": 1, "source": "x.txt", "snippet": "a b c"})
        self.assertTrue(out[1]["snippet"].endswith("…"))
        self.assertLessEqual(len(out[1]["snippet"]), 51)

    def test_missing_metadata(self):
        out = format_sources([SimpleNamespace(page_content="t", metadata=None)])
        self.assertEqual(out[0]["source"], "unknown")


class ChatbotTests(unittest.TestCase):
    def test_finance_chat_delegates_with_history(self):
        from app.rag import chatbot
        with patch("app.rag.chatbot.ask_tutor", return_value=("a", [])) as m:
            self.assertEqual(chatbot.finance_chat("q", history=[1], report_context="r"), ("a", []))
        self.assertEqual(m.call_args.kwargs["history"], [1])
        self.assertEqual(m.call_args.kwargs["report_context"], "r")


class LLMWrapperTests(unittest.TestCase):
    def test_missing_key_raises_config_error(self):
        from app.llm import llm_model
        llm_model.get_llm.cache_clear()
        with patch("app.config.get_groq_api_key", return_value=None):
            with self.assertRaises(LLMConfigError):
                llm_model.get_llm()

    def test_failures_are_wrapped(self):
        from app.errors import LLMError
        from app.llm import llm_model
        broken = MagicMock()
        broken.invoke.side_effect = RuntimeError("rate limited")
        with patch("app.llm.llm_model.get_llm", return_value=broken):
            with self.assertRaises(LLMError) as ctx:
                llm_model.invoke_llm("hi")
        self.assertIn("rate limited", str(ctx.exception))

    def test_returns_content(self):
        from app.llm import llm_model
        ok = MagicMock()
        ok.invoke.return_value = SimpleNamespace(content="hello")
        with patch("app.llm.llm_model.get_llm", return_value=ok):
            self.assertEqual(llm_model.invoke_llm("hi"), "hello")


if __name__ == "__main__":
    unittest.main()
