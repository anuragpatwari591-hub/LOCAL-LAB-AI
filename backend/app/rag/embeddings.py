"""Local, fully offline text embeddings.

We deliberately do NOT depend on downloading a neural embedding model from
Hugging Face or any other network source: this sandbox's network policy
blocks Hugging Face/ModelScope, and more importantly the shipped USB
product must work with zero network calls at runtime.

`HashingEmbedder` implements the classic feature-hashing trick (a
deterministic bag-of-words -> fixed-dimension vector projection, similar in
spirit to scikit-learn's HashingVectorizer). It needs no model file, no
download, and no GPU, and is fast enough for a low-end CPU. It is less
semantically rich than a trained neural embedding model, but it is real,
local, dependency-free, and testable end-to-end today.

The interface is intentionally small so a stronger local embedding backend
(e.g. a GGUF embedding model run through the same llama.cpp engine, dropped
into models/embeddings/ by a future `prepare` run with real internet
access) can be swapped in later without touching callers.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

import numpy as np

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class BaseEmbedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, text: str) -> np.ndarray: ...

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.stack([self.embed(t) for t in texts]) if texts else np.zeros((0, self.dim))


class HashingEmbedder(BaseEmbedder):
    """Deterministic hashing-trick embedding with TF-IDF-style weighting.

    Each token is hashed (SHA-256, stable across processes/platforms,
    unlike Python's salted `hash()`) into one of `dim` buckets with a
    deterministic +1/-1 sign to reduce collision bias, weighted by
    log-scaled term frequency, then L2-normalized.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _bucket_and_sign(self, token: str) -> tuple[int, float]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "little") % self.dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        return bucket, sign

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = tokenize(text)
        if not tokens:
            return vec

        counts: dict[str, int] = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1

        for tok, count in counts.items():
            bucket, sign = self._bucket_and_sign(tok)
            weight = sign * (1.0 + math.log(count))
            vec[bucket] += weight

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / denom)


_default_embedder: HashingEmbedder | None = None


def get_default_embedder(dim: int = 256) -> HashingEmbedder:
    global _default_embedder
    if _default_embedder is None or _default_embedder.dim != dim:
        _default_embedder = HashingEmbedder(dim=dim)
    return _default_embedder
