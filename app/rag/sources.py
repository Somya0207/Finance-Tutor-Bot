"""Turn retrieved chunks into citation info for the UI."""


def format_sources(docs, snippet_chars=240):
    """Return [{'n', 'source', 'snippet'}] with one entry per retrieved chunk."""
    out = []
    for i, d in enumerate(docs, 1):
        meta = getattr(d, "metadata", {}) or {}
        text = " ".join(getattr(d, "page_content", "").split())
        if len(text) > snippet_chars:
            text = text[:snippet_chars].rstrip() + "…"
        out.append({"n": i, "source": meta.get("source", "unknown"), "snippet": text})
    return out
