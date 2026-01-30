from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    chunk_index: int


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[Chunk]:
    if max_chars <= 200:
        raise ValueError("max_chars must be > 200")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be in [0, max_chars)")

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        joined = "\n\n".join(buf).strip()
        if joined:
            chunks.append(joined)
        buf = []
        buf_len = 0

    for p in paras:
        if buf_len + len(p) + 2 <= max_chars:
            buf.append(p)
            buf_len += len(p) + 2
            continue

        flush()
        if len(p) > max_chars:
            start = 0
            while start < len(p):
                end = min(start + max_chars, len(p))
                chunks.append(p[start:end].strip())
                start = max(0, end - overlap_chars)
        else:
            buf.append(p)
            buf_len = len(p)

    flush()

    out: list[Chunk] = []
    prev_tail = ""
    for i, c in enumerate(chunks):
        merged = (prev_tail + "\n" + c).strip() if prev_tail and overlap_chars > 0 else c
        out.append(Chunk(text=merged, chunk_index=i))
        prev_tail = c[-overlap_chars:] if overlap_chars > 0 else ""

    return out
