import sys
import types
import unittest
from unittest.mock import patch

from app.rag import compat


def fake_module(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    return m


class CompatTests(unittest.TestCase):
    def test_prefers_dedicated_package(self):
        new, old = object(), object()
        mods = {"langchain_chroma": fake_module("langchain_chroma", Chroma=new),
                "langchain_community": fake_module("langchain_community"),
                "langchain_community.vectorstores": fake_module("x", Chroma=old)}
        with patch.dict(sys.modules, mods):
            self.assertIs(compat.get_chroma_class(), new)

    def test_falls_back_to_community(self):
        old = object()
        mods = {"langchain_chroma": None,  # None in sys.modules makes the import fail
                "langchain_community": fake_module("langchain_community"),
                "langchain_community.vectorstores": fake_module("x", Chroma=old)}
        with patch.dict(sys.modules, mods):
            self.assertIs(compat.get_chroma_class(), old)

    def test_helpful_error_when_nothing_installed(self):
        mods = {"langchain_chroma": None, "langchain_community.vectorstores": None,
                "langchain_huggingface": None, "langchain_community.embeddings": None}
        with patch.dict(sys.modules, mods):
            with self.assertRaisesRegex(ImportError, "langchain-chroma"):
                compat.get_chroma_class()
            with self.assertRaisesRegex(ImportError, "langchain-huggingface"):
                compat.get_hf_embeddings_class()

    def test_embeddings_prefers_dedicated_package(self):
        new = object()
        with patch.dict(sys.modules, {"langchain_huggingface": fake_module("h", HuggingFaceEmbeddings=new)}):
            self.assertIs(compat.get_hf_embeddings_class(), new)


if __name__ == "__main__":
    unittest.main()
