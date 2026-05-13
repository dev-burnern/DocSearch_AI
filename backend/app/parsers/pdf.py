import fitz

from backend.app.parsers.base import ParsedDocument, build_parsed_document


class PdfParser:
    name = "pdf"
    supported_extensions = (".pdf",)

    def parse(self, data: bytes) -> ParsedDocument:
        document = fitz.open(stream=data, filetype="pdf")
        try:
            text = "\n".join(page.get_text("text") for page in document)
        finally:
            document.close()

        return build_parsed_document(parser_name=self.name, text=text)
