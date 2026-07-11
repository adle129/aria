"""Read docx body blocks (paragraphs + tables) in document order."""

from __future__ import annotations

from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.ingest.docx_numbering import DocxNumberingState, paragraph_text_with_numbering


def iter_block_items(parent: DocxDocument):
    """Yield Paragraph and Table elements in reading order."""
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def table_to_lines(table: Table) -> list[str]:
    lines: list[str] = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\r", " ").replace("\n", " ") for cell in row.cells]
        if any(cells):
            lines.append(" | ".join(cells))
    return lines


def docx_to_ordered_text(doc: DocxDocument) -> str:
    """Flatten docx to text with [TABLE] rows interleaved at correct positions."""
    parts: list[str] = []
    numbering = DocxNumberingState(doc)

    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = paragraph_text_with_numbering(block, numbering)
            if text:
                parts.append(text)
        else:
            for line in table_to_lines(block):
                parts.append(f"[TABLE] {line}")

    return "\n".join(parts)
