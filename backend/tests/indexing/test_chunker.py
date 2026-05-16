from backend.app.indexing.chunker import CharacterChunker


def test_chunker_prefers_word_boundaries() -> None:
    chunker = CharacterChunker(max_characters=12, overlap_characters=0)

    chunks = chunker.chunk("alpha beta gamma")

    assert chunks == ["alpha beta", "gamma"]


def test_chunker_normalizes_repeated_whitespace() -> None:
    chunker = CharacterChunker(max_characters=20, overlap_characters=0)

    chunks = chunker.chunk("alpha\n\n  beta\tgamma")

    assert chunks == ["alpha beta gamma"]
