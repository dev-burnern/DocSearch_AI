from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


PREVIEW_LIMIT = 200


class DocumentProcessingError(ValueError):
    code = "DOCUMENT_PROCESSING_FAILED"


class UnsupportedDocumentTypeError(DocumentProcessingError):
    code = "DOCUMENT_UNSUPPORTED_TYPE"


class EmptyDocumentError(DocumentProcessingError):
    code = "DOCUMENT_EMPTY"


class CorruptDocumentError(DocumentProcessingError):
    code = "DOCUMENT_CORRUPT"


class DocumentTooLargeError(DocumentProcessingError):
    code = "DOCUMENT_TOO_LARGE"


@dataclass(frozen=True)
class ParsedDocument:
    parser_name: str
    text: str
    preview: str
    character_count: int


class DocumentParser(Protocol):
    name: str
    supported_extensions: tuple[str, ...]

    def parse(self, data: bytes) -> ParsedDocument:
        ...


def build_parsed_document(*, parser_name: str, text: str) -> ParsedDocument:
    normalized_text = normalize_text(text)
    if not normalized_text:
        raise EmptyDocumentError("Document is empty after parsing.")

    return ParsedDocument(
        parser_name=parser_name,
        text=normalized_text,
        preview=normalized_text[:PREVIEW_LIMIT],
        character_count=len(normalized_text),
    )


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


class ParserRegistry:
    def __init__(self, parsers: Iterable[DocumentParser] | None = None) -> None:
        selected_parsers = tuple(parsers or self._default_parsers())
        self._parsers: dict[str, DocumentParser] = {}

        for parser in selected_parsers:
            for extension in parser.supported_extensions:
                self._parsers[extension.lower()] = parser

    def parse(self, *, filename: str, data: bytes) -> ParsedDocument:
        extension = Path(filename).suffix.lower()
        parser = self._parsers.get(extension)
        if parser is None:
            raise UnsupportedDocumentTypeError(f"Unsupported document type: {extension}")

        return parser.parse(data)

    @staticmethod
    def _default_parsers() -> tuple[DocumentParser, ...]:
        from backend.app.parsers.markdown import MarkdownParser
        from backend.app.parsers.pdf import PdfParser
        from backend.app.parsers.text import TextParser
        from backend.app.parsers.docx import DocxParser

        return (TextParser(), MarkdownParser(), PdfParser(), DocxParser())
