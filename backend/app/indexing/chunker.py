class CharacterChunker:
    def __init__(self, *, max_characters: int, overlap_characters: int) -> None:
        if max_characters <= 0:
            raise ValueError("max_characters must be positive.")
        if overlap_characters < 0:
            raise ValueError("overlap_characters must be zero or positive.")
        if overlap_characters >= max_characters:
            raise ValueError("overlap_characters must be smaller than max_characters.")

        self._max_characters = max_characters
        self._overlap_characters = overlap_characters

    def chunk(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0

        while start < len(normalized):
            end = self._find_chunk_end(normalized, start)
            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= len(normalized):
                break

            start = max(end - self._overlap_characters, start + 1)

        return chunks

    def _find_chunk_end(self, text: str, start: int) -> int:
        hard_end = min(start + self._max_characters, len(text))
        if hard_end == len(text):
            return hard_end

        window = text[start:hard_end]
        split_at = window.rfind(" ")
        if split_at <= 0:
            return hard_end

        return start + split_at
