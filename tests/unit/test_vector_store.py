from app.rag.store import VectorStore


def test_add_and_search_document(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def factorial(n):\n"
        "    if n == 0:\n"
        "        return 1\n"
        "    return n * factorial(n - 1)\n"
    )

    store = VectorStore(db_path=tmp_path / "rag.db")
    result = store.add_document(sample)
    assert result["chunk_count"] >= 1

    hits = store.search("recursive factorial function")
    assert len(hits) >= 1
    assert hits[0]["source"] == "sample.py"


def test_delete_document_removes_chunks(tmp_path):
    sample = tmp_path / "sample.txt"
    sample.write_text("Operating systems manage processes and memory.")

    store = VectorStore(db_path=tmp_path / "rag.db")
    result = store.add_document(sample)
    store.delete_document(result["document_id"])

    assert store.list_documents() == []
    assert store.search("processes") == []


def test_project_scoped_search(tmp_path):
    store = VectorStore(db_path=tmp_path / "rag.db")

    f1 = tmp_path / "a.txt"
    f1.write_text("Content about Oracle PL/SQL triggers.")
    f2 = tmp_path / "b.txt"
    f2.write_text("Content about Linux shell scripting.")

    store.add_document(f1, project_id="p1")
    store.add_document(f2, project_id="p2")

    p1_hits = store.search("triggers", project_id="p1")
    p2_hits = store.search("triggers", project_id="p2")
    assert len(p1_hits) >= 1
    assert all(h["source"] == "a.txt" for h in p1_hits)
    assert p2_hits == [] or all(h["source"] != "a.txt" for h in p2_hits)
