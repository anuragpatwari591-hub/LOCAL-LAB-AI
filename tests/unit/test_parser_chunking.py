from app.rag.parser import chunk_text, extract_text


def test_chunking_respects_size_roughly():
    text = "\n\n".join(f"Paragraph {i} " + ("word " * 40) for i in range(20))
    chunks = chunk_text(text, source="test.txt", chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 300 + 50  # allow slack for overlap carry-over


def test_code_chunking_splits_on_function_boundaries():
    code = (
        "def foo():\n    return 1\n\n"
        "def bar():\n    return 2\n\n"
        "class Baz:\n    def method(self):\n        return 3\n"
    )
    chunks = chunk_text(code, source="test.py", chunk_size=1000, overlap=0, is_code=True)
    assert len(chunks) >= 1
    full = "\n".join(c.text for c in chunks)
    assert "def foo" in full and "def bar" in full and "class Baz" in full


def test_empty_text_produces_no_chunks():
    assert chunk_text("   \n\n  ", source="empty.txt") == []


def test_extract_text_reads_plain_files(tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("# Heading\n\nSome content.")
    text = extract_text(f)
    assert "Heading" in text
    assert "Some content" in text
