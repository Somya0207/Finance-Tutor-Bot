import unittest

from app import config
from app.rag.loader import list_source_files, read_file_text
from eval import retrieval_eval as ev


class SeedDataTests(unittest.TestCase):
    def test_no_empty_seed_files(self):
        files = list_source_files()
        self.assertGreaterEqual(len(files), 5)
        for f in files:
            self.assertGreater(len(read_file_text(f)), 200, f"{f.name} is empty or tiny")

    def test_every_eval_question_is_answerable_from_its_source(self):
        questions = ev.load_questions()
        self.assertGreaterEqual(len(questions), 10)
        self.assertEqual(ev.find_bad_questions(questions), [])

    def test_find_bad_questions_flags_problems(self):
        bad = ev.find_bad_questions([
            {"question": "a", "source": "does_not_exist.txt", "key_fact": "x"},
            {"question": "b", "source": "bonds.txt", "key_fact": "definitely not in the file"},
        ])
        self.assertEqual([why for _, why in bad], ["source file not found", "key fact not in source"])


class ScoringTests(unittest.TestCase):
    QS = [{"question": "q1", "key_fact": "alpha"}, {"question": "q2", "key_fact": "beta"},
          {"question": "q3", "key_fact": "gamma"}]

    def test_hit_rate_mrr_and_context_size(self):
        retrieved = [["x", "has ALPHA here"],  # hit at rank 2
                     ["beta"],                  # hit at rank 1
                     ["nothing", "relevant"]]   # miss
        s = ev.score_results(retrieved, self.QS, k=4)
        self.assertEqual(s["hit@4"], round(2 / 3, 3))
        self.assertEqual(s["MRR"], round((0.5 + 1.0 + 0) / 3, 3))
        self.assertEqual(s["avg_context_chars"], round((1 + 14 + 4 + 7 + 8) / 3))

    def test_whitespace_differences_do_not_cause_misses(self):
        qs = [{"question": "q", "key_fact": "risk adjusted performance"}]
        self.assertEqual(ev.score_results([["risk\n  adjusted   performance"]], qs)["hit@4"], 1.0)


class ConfigTests(unittest.TestCase):
    def test_paths_are_absolute(self):
        for p in (config.DATA_DIR, config.VECTOR_DB_DIR, config.APP_DB_PATH):
            self.assertTrue(p.is_absolute())

    def test_api_key_from_env(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"GROQ_API": "abc"}):
            self.assertEqual(config.get_groq_api_key(), "abc")

    def test_login_required_flag(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"REQUIRE_LOGIN": "true"}):
            self.assertTrue(config.login_required())
        with patch.dict(os.environ, {"REQUIRE_LOGIN": ""}):
            self.assertFalse(config.login_required())

    def test_llm_settings_exist(self):
        self.assertIsInstance(config.LLM_MAX_TOKENS, int)
        self.assertTrue(config.LLM_MODEL)

if __name__ == "__main__":
    unittest.main()
