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
        normalized = text.strip()
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        step = self._max_characters - self._overlap_characters

        while start < len(normalized):
            end = start + self._max_characters
            chunks.append(normalized[start:end])
            start += step

        return chunks
