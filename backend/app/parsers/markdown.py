import re

from backend.app.parsers.base import (
    CorruptDocumentError,
    ParsedDocument,
    build_parsed_document,
)


class MarkdownParser:
    name = "markdown"
    supported_extensions = (".md", ".markdown")

    def parse(self, data: bytes) -> ParsedDocument:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CorruptDocumentError("Document is not valid UTF-8.") from exc

        cleaned = re.sub(r"`+", "", text)
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
        return build_parsed_document(parser_name=self.name, text=cleaned)
