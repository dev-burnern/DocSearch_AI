from backend.app.parsers.base import (
    CorruptDocumentError,
    ParsedDocument,
    build_parsed_document,
)


class TextParser:
    name = "text"
    supported_extensions = (".txt",)

    def parse(self, data: bytes) -> ParsedDocument:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CorruptDocumentError("Document is not valid UTF-8.") from exc

        return build_parsed_document(parser_name=self.name, text=text)
