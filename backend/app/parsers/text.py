from backend.app.parsers.base import ParsedDocument, build_parsed_document


class TextParser:
    name = "text"
    supported_extensions = (".txt",)

    def parse(self, data: bytes) -> ParsedDocument:
        text = data.decode("utf-8", errors="replace")
        return build_parsed_document(parser_name=self.name, text=text)
