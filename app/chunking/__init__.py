"""
Korean-Optimized Text Chunking
한국어 문서에 최적화된 청크 분할
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import settings


@dataclass
class Chunk:
    """A text chunk with metadata"""
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    heading: Optional[str] = None
    has_table: bool = False
    has_image: bool = False
    page: Optional[int] = None
    sheet: Optional[str] = None
    slide: Optional[int] = None
    metadata: dict = field(default_factory=dict)


class KoreanTextChunker:
    """
    Korean-optimized text chunker
    
    Features:
    - Sentence boundary detection using Korean NLP
    - Respects paragraph boundaries
    - Handles tables as single chunks when possible
    - Configurable overlap for context preservation
    """
    
    def __init__(
        self,
        max_chars: int = settings.chunk_max_chars,
        overlap_chars: int = settings.chunk_overlap_chars,
        respect_sentences: bool = settings.chunk_respect_sentences,
    ):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.respect_sentences = respect_sentences
        self._kiwi = None
    
    @property
    def kiwi(self):
        """Lazy load Kiwi Korean tokenizer"""
        if self._kiwi is None and self.respect_sentences:
            try:
                from kiwipiepy import Kiwi
                self._kiwi = Kiwi()
            except ImportError:
                pass
        return self._kiwi
    
    def chunk(
        self,
        text: str,
        page: int | None = None,
        sheet: str | None = None,
        slide: int | None = None,
        heading: str | None = None,
        is_table: bool = False,
    ) -> list[Chunk]:
        """
        Split text into chunks
        
        Args:
            text: The text to chunk
            page: Optional page number
            sheet: Optional sheet name (for Excel)
            slide: Optional slide number (for PPT)
            heading: Optional section heading
            is_table: Whether the text is a table
        
        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        
        # Tables: try to keep as single chunk if small enough
        if is_table and len(text) <= self.max_chars * 1.5:
            return [Chunk(
                text=text,
                chunk_index=0,
                char_start=0,
                char_end=len(text),
                heading=heading,
                has_table=True,
                page=page,
                sheet=sheet,
                slide=slide,
            )]
        
        # Split into sentences
        if self.respect_sentences and self.kiwi:
            sentences = self._split_sentences_kiwi(text)
        else:
            sentences = self._split_sentences_regex(text)
        
        # Build chunks from sentences
        chunks = self._build_chunks(
            sentences,
            page=page,
            sheet=sheet,
            slide=slide,
            heading=heading,
            is_table=is_table,
        )
        
        return chunks
    
    def _split_sentences_kiwi(self, text: str) -> list[tuple[str, int, int]]:
        """Split text into sentences using Kiwi"""
        sentences = []
        for sent in self.kiwi.split_into_sents(text):
            sentences.append((sent.text, sent.start, sent.end))
        return sentences
    
    def _split_sentences_regex(self, text: str) -> list[tuple[str, int, int]]:
        """Split text into sentences using regex (fallback)"""
        # Korean sentence endings: 다, 요, 죠, !, ?, .
        # Also handle numbered lists, bullets, etc.
        pattern = r'(?<=[.!?다요죠])\s+(?=[가-힣A-Z0-9\-\*\•\d])'
        
        sentences = []
        last_end = 0
        
        for match in re.finditer(pattern, text):
            sent_text = text[last_end:match.start() + 1].strip()
            if sent_text:
                sentences.append((sent_text, last_end, match.start() + 1))
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                sentences.append((remaining, last_end, len(text)))
        
        # If no sentences found, treat paragraphs as sentences
        if not sentences:
            for match in re.finditer(r'[^\n]+', text):
                sent_text = match.group().strip()
                if sent_text:
                    sentences.append((sent_text, match.start(), match.end()))
        
        return sentences if sentences else [(text, 0, len(text))]
    
    def _build_chunks(
        self,
        sentences: list[tuple[str, int, int]],
        page: int | None = None,
        sheet: str | None = None,
        slide: int | None = None,
        heading: str | None = None,
        is_table: bool = False,
    ) -> list[Chunk]:
        """Build chunks from sentences with overlap"""
        if not sentences:
            return []
        
        chunks: list[Chunk] = []
        current_texts: list[str] = []
        current_len = 0
        chunk_start = sentences[0][1]
        
        for sent_text, sent_start, sent_end in sentences:
            sent_len = len(sent_text)
            
            # Check if adding this sentence would exceed max
            if current_len + sent_len + 1 > self.max_chars and current_texts:
                # Save current chunk
                chunk_text = " ".join(current_texts)
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_index=len(chunks),
                    char_start=chunk_start,
                    char_end=sent_start,
                    heading=heading,
                    has_table=is_table,
                    page=page,
                    sheet=sheet,
                    slide=slide,
                ))
                
                # Start new chunk with overlap
                overlap_texts = self._get_overlap_texts(current_texts, chunk_text)
                current_texts = overlap_texts + [sent_text]
                current_len = sum(len(t) for t in current_texts) + len(current_texts) - 1
                chunk_start = sent_start - len(" ".join(overlap_texts)) if overlap_texts else sent_start
            else:
                current_texts.append(sent_text)
                current_len += sent_len + (1 if current_texts else 0)
            
            # Handle very long sentences
            if sent_len > self.max_chars:
                # Flush current
                if len(current_texts) > 1:
                    chunk_text = " ".join(current_texts[:-1])
                    chunks.append(Chunk(
                        text=chunk_text,
                        chunk_index=len(chunks),
                        char_start=chunk_start,
                        char_end=sent_start,
                        heading=heading,
                        has_table=is_table,
                        page=page,
                        sheet=sheet,
                        slide=slide,
                    ))
                
                # Split long sentence
                long_chunks = self._split_long_text(sent_text, sent_start)
                for lc_text, lc_start, lc_end in long_chunks:
                    chunks.append(Chunk(
                        text=lc_text,
                        chunk_index=len(chunks),
                        char_start=lc_start,
                        char_end=lc_end,
                        heading=heading,
                        has_table=is_table,
                        page=page,
                        sheet=sheet,
                        slide=slide,
                    ))
                
                current_texts = []
                current_len = 0
                chunk_start = sent_end
        
        # Don't forget the last chunk
        if current_texts:
            chunk_text = " ".join(current_texts)
            chunks.append(Chunk(
                text=chunk_text,
                chunk_index=len(chunks),
                char_start=chunk_start,
                char_end=sentences[-1][2],
                heading=heading,
                has_table=is_table,
                page=page,
                sheet=sheet,
                slide=slide,
            ))
        
        return chunks
    
    def _get_overlap_texts(self, texts: list[str], full_text: str) -> list[str]:
        """Get texts for overlap from previous chunk"""
        if not texts or self.overlap_chars <= 0:
            return []
        
        overlap_texts = []
        overlap_len = 0
        
        for text in reversed(texts):
            if overlap_len + len(text) <= self.overlap_chars:
                overlap_texts.insert(0, text)
                overlap_len += len(text) + 1
            else:
                # Take partial text if needed
                remaining = self.overlap_chars - overlap_len
                if remaining > 50:  # Only if meaningful amount
                    overlap_texts.insert(0, text[-remaining:])
                break
        
        return overlap_texts
    
    def _split_long_text(
        self,
        text: str,
        base_start: int,
    ) -> list[tuple[str, int, int]]:
        """Split a long text that exceeds max_chars"""
        chunks = []
        step = self.max_chars - self.overlap_chars
        
        for i in range(0, len(text), step):
            end = min(i + self.max_chars, len(text))
            chunk_text = text[i:end]
            chunks.append((
                chunk_text,
                base_start + i,
                base_start + end,
            ))
            
            if end >= len(text):
                break
        
        return chunks


# Default chunker instance
_chunker: KoreanTextChunker | None = None


def get_chunker() -> KoreanTextChunker:
    """Get the default chunker instance"""
    global _chunker
    if _chunker is None:
        _chunker = KoreanTextChunker()
    return _chunker


def chunk_text(
    text: str,
    max_chars: int | None = None,
    overlap_chars: int | None = None,
    **kwargs,
) -> list[Chunk]:
    """
    Convenience function to chunk text
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk (default: from settings)
        overlap_chars: Overlap characters between chunks (default: from settings)
        **kwargs: Additional arguments passed to chunk()
    
    Returns:
        List of Chunk objects
    """
    if max_chars or overlap_chars:
        chunker = KoreanTextChunker(
            max_chars=max_chars or settings.chunk_max_chars,
            overlap_chars=overlap_chars or settings.chunk_overlap_chars,
        )
    else:
        chunker = get_chunker()
    
    return chunker.chunk(text, **kwargs)
