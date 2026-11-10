"""End-to-end vector-store tests with a fake embedding model (no model download).
Skipped automatically when chromadb / langchain are not installed."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HAVE_STACK = (all(importlib.util.find_spec(m) for m in
                  ("chromadb", "langchain_core", "langchain_text_splitters"))
              and any(importlib.util.find_spec(m) for m in ("langchain_chroma", "langchain_community")))


@unittest.skipUnless(HAVE_STACK, "chromadb/langchain not installed")
class PipelineTests(unittest.TestCase):
    def setUp(self):
        from langchain_core.embeddings import Embeddings

        class BagOfWords(Embeddings):
            DIM = 256

            def _vec(self, text):
                v = [0.0] * self.DIM
                for w in text.lower().split():
                    v[hash(w.strip(".,?")) % self.DIM] += 1.0
                return v

            def embed_documents(self, texts):
                return [self._vec(t) for t in texts]

            def embed_query(self, text):
                return self._vec(text)

        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)  # Windows keeps Chroma files open
        self.db_dir = Path(self.tmp.name) / "vdb"
        self.data_dir = Path(self.tmp.name) / "data"
        self.data_dir.mkdir()
        fake = BagOfWords()
        self.patches = [patch("app.rag.vector_store.get_embeddings", return_value=fake),
                        patch("app.rag.embedding.get_embeddings", return_value=fake)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        from app.rag.compat import release_chroma
        release_chroma()
        self.tmp.cleanup()

    def docs(self, **files):
        from langchain_core.documents import Document
        return [Document(page_content=t, metadata={"source": n}) for n, t in files.items()]

    def test_create_search_and_replace_by_source(self):
        from app.rag import vector_store as vs
        from app.rag.retriever import get_retriever

        vs.create_vector_store(self.docs(**{"bonds.txt": "bond duration measures rate sensitivity",
                                            "fx.txt": "currency swaps exchange cash flows"}),
                               persist_directory=self.db_dir)
        self.assertTrue(vs.vector_store_exists(self.db_dir))
        top = get_retriever(self.db_dir, k=1).invoke("what does bond duration measure")[0]
        self.assertEqual(top.metadata["source"], "bonds.txt")

        # re-adding a source replaces its chunks instead of duplicating them
        vs.add_documents(self.docs(**{"bonds.txt": "completely rewritten convexity text"}),
                         persist_directory=self.db_dir)
        results = get_retriever(self.db_dir, k=10).invoke("bond")
        self.assertEqual(sum(d.metadata["source"] == "bonds.txt" for d in results), 1)

    def test_rebuilding_replaces_the_old_index(self):
        from app.rag import vector_store as vs
        from app.rag.retriever import get_retriever
        vs.create_vector_store(self.docs(**{"old.txt": "old bond text"}), persist_directory=self.db_dir)
        vs.create_vector_store(self.docs(**{"new.txt": "new bond text"}), persist_directory=self.db_dir)
        sources = {d.metadata["source"] for d in get_retriever(self.db_dir, k=10).invoke("bond")}
        self.assertEqual(sources, {"new.txt"})

    def test_empty_inputs_raise_friendly_errors(self):
        from app.errors import KnowledgeBaseEmpty
        from app.rag import vector_store as vs
        from app.rag.retriever import get_retriever
        with self.assertRaises(KnowledgeBaseEmpty):
            vs.create_vector_store([], persist_directory=self.db_dir)
        with self.assertRaises(KnowledgeBaseEmpty):
            get_retriever(self.db_dir)

    def test_ensure_vector_db_builds_once(self):
        from app.rag import vector_store as vs
        (self.data_dir / "n.txt").write_text("diversification reduces risk " * 5)
        with patch("app.config.DATA_DIR", self.data_dir), \
             patch("app.rag.loader.config.DATA_DIR", self.data_dir):
            self.assertTrue(vs.ensure_vector_db(self.db_dir))
            self.assertFalse(vs.ensure_vector_db(self.db_dir))

    def test_chunking_variants(self):
        from app.rag import vector_store as vs
        d = self.docs(a="word " * 600)
        self.assertEqual(len(vs.split_documents(d, None)), 1)
        self.assertGreater(len(vs.split_documents(d, 500, 50)), len(vs.split_documents(d, 1000, 100)))


if __name__ == "__main__":
    unittest.main()