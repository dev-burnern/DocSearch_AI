from io import BytesIO
import zipfile
from xml.etree import ElementTree

from backend.app.parsers.base import (
    CorruptDocumentError,
    ParsedDocument,
    build_parsed_document,
)


class DocxParser:
    name = "docx"
    supported_extensions = (".docx",)

    def parse(self, data: bytes) -> ParsedDocument:
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                document_xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(document_xml)
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise CorruptDocumentError("DOCX document is corrupt or unreadable.") from exc

        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        text = " ".join(
            node.text or ""
            for node in root.iter(f"{namespace}t")
            if node.text
        )
        return build_parsed_document(parser_name=self.name, text=text)
