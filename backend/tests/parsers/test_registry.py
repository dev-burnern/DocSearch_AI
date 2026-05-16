import fitz
import pytest
from io import BytesIO
import zipfile


def create_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    return document.tobytes()


def create_docx_bytes(text: str) -> bytes:
    document_xml = f"""
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
      </w:body>
    </w:document>
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_txt_파서가_텍스트를_그대로_추출한다() -> None:
    from backend.app.parsers.base import ParserRegistry

    registry = ParserRegistry()

    parsed = registry.parse(filename="memo.txt", data=b"hello parser")

    assert parsed.parser_name == "text"
    assert parsed.text == "hello parser"
    assert parsed.preview == "hello parser"
    assert parsed.character_count == len("hello parser")


def test_markdown_파서가_마크다운_기호를_정리한다() -> None:
    from backend.app.parsers.base import ParserRegistry

    registry = ParserRegistry()

    parsed = registry.parse(
        filename="notes.md",
        data="# 제목\n- 첫번째 항목\n`코드`".encode("utf-8"),
    )

    assert parsed.parser_name == "markdown"
    assert "제목" in parsed.text
    assert "첫번째 항목" in parsed.text
    assert "#" not in parsed.text
    assert "`" not in parsed.text


def test_pdf_파서가_pdf_본문을_추출한다() -> None:
    from backend.app.parsers.base import ParserRegistry

    registry = ParserRegistry()

    parsed = registry.parse(
        filename="guide.pdf",
        data=create_pdf_bytes("PDF body"),
    )

    assert parsed.parser_name == "pdf"
    assert "PDF body" in parsed.text


def test_지원하지_않는_확장자는_오류를_낸다() -> None:
    from backend.app.parsers.base import ParserRegistry

    registry = ParserRegistry()

    with pytest.raises(ValueError, match="Unsupported document type: \\.csv"):
        registry.parse(filename="data.csv", data=b"a,b,c")


def test_docx_parser_extracts_document_text() -> None:
    from backend.app.parsers.base import ParserRegistry

    registry = ParserRegistry()

    parsed = registry.parse(
        filename="guide.docx",
        data=create_docx_bytes("DOCX body"),
    )

    assert parsed.parser_name == "docx"
    assert parsed.text == "DOCX body"
    assert parsed.preview == "DOCX body"


def test_parser_rejects_empty_text_documents() -> None:
    from backend.app.parsers.base import EmptyDocumentError, ParserRegistry

    registry = ParserRegistry()

    with pytest.raises(EmptyDocumentError, match="Document is empty"):
        registry.parse(filename="empty.txt", data=b" \n\t ")


def test_parser_rejects_invalid_utf8_text_documents() -> None:
    from backend.app.parsers.base import CorruptDocumentError, ParserRegistry

    registry = ParserRegistry()

    with pytest.raises(CorruptDocumentError, match="valid UTF-8"):
        registry.parse(filename="broken.txt", data=b"\xff\xfe\xfd")


def test_parser_rejects_corrupt_pdf_documents() -> None:
    from backend.app.parsers.base import CorruptDocumentError, ParserRegistry

    registry = ParserRegistry()

    with pytest.raises(CorruptDocumentError, match="PDF document is corrupt"):
        registry.parse(filename="broken.pdf", data=b"not a pdf")


def test_parser_rejects_corrupt_docx_documents() -> None:
    from backend.app.parsers.base import CorruptDocumentError, ParserRegistry

    registry = ParserRegistry()

    with pytest.raises(CorruptDocumentError, match="DOCX document is corrupt"):
        registry.parse(filename="broken.docx", data=b"not a docx")
