import numpy as np
from app.rag.embeddings import HashingEmbedder, cosine_similarity


def test_embedding_is_deterministic():
    embedder = HashingEmbedder(dim=128)
    a = embedder.embed("SELECT * FROM students WHERE marks > 90")
    b = embedder.embed("SELECT * FROM students WHERE marks > 90")
    assert np.allclose(a, b)


def test_embedding_is_normalized():
    embedder = HashingEmbedder(dim=128)
    vec = embedder.embed("some text with several different words in it")
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-5


def test_empty_text_gives_zero_vector():
    embedder = HashingEmbedder(dim=64)
    vec = embedder.embed("")
    assert np.allclose(vec, np.zeros(64))


def test_similar_texts_score_higher_than_unrelated():
    embedder = HashingEmbedder(dim=256)
    query = embedder.embed("how to implement a stack push and pop in java")
    related = embedder.embed("class Stack with push and pop methods in Java")
    unrelated = embedder.embed("Oracle PL/SQL trigger for auditing salary updates")

    score_related = cosine_similarity(query, related)
    score_unrelated = cosine_similarity(query, unrelated)
    assert score_related > score_unrelated


def test_no_network_access_required(monkeypatch):
    """Embedding must never attempt any network call."""
    import socket

    def _blocked(*args, **kwargs):
        raise AssertionError("Embedding must not open network sockets")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    embedder = HashingEmbedder(dim=64)
    embedder.embed("no network needed for this")
