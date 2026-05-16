import fitz

from backend.app.parsers.base import (
    CorruptDocumentError,
    ParsedDocument,
    build_parsed_document,
)


class PdfParser:
    name = "pdf"
    supported_extensions = (".pdf",)

    def parse(self, data: bytes) -> ParsedDocument:
        try:
            document = fitz.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise CorruptDocumentError("PDF document is corrupt or unreadable.") from exc

        try:
            text = "\n".join(page.get_text("text") for page in document)
        except Exception as exc:
            raise CorruptDocumentError("PDF document is corrupt or unreadable.") from exc
        finally:
            document.close()

        return build_parsed_document(parser_name=self.name, text=text)
