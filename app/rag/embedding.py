from functools import lru_cache

from app import config


@lru_cache(maxsize=1)
def get_embeddings():
    """Load the embedding model once per process (it is the slow part)."""
    from app.rag.compat import get_hf_embeddings_class

    return get_hf_embeddings_class()(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )
