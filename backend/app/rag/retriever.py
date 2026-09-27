"""Format retrieved chunks into an LLM-ready context block."""

from __future__ import annotations

from .store import VectorStore


def build_context_block(
    store: VectorStore, query: str, top_k: int = 5, project_id: str | None = None
) -> tuple[str, list[dict]]:
    results = store.search(query, top_k=top_k, project_id=project_id)
    if not results:
        return "", []

    lines = ["Relevant excerpts from the user's uploaded documents:"]
    for i, r in enumerate(results, start=1):
        lines.append(f"\n[{i}] (source: {r['source']}, relevance: {r['score']})\n{r['text']}")

    return "\n".join(lines), results
