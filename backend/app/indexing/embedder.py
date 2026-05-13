import hashlib
from typing import Protocol


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class DeterministicEmbedder:
    def __init__(self, *, vector_size: int) -> None:
        if vector_size <= 0:
            raise ValueError("vector_size must be positive.")
        self._vector_size = vector_size

    @property
    def vector_size(self) -> int:
        return self._vector_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [round(byte / 255, 6) for byte in digest[: self._vector_size]]
            vectors.append(vector)
        return vectors
