"""Word (.docx) to Markdown converter."""

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table

from converters.base import AbstractConverter
from utils.image_utils import image_to_base64
from utils.table_utils import rows_to_markdown_table


class DocxConverter(AbstractConverter):
    """Convert Word .docx files to Markdown."""

    def convert(self, file_path: str, options: dict | None = None) -> str:
        options = options or {}
        max_width = options.get('max_image_width', 800)

        doc = Document(file_path)
        md_lines = []

        for element in doc.element.body:
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

            if tag == 'p':
                para = self._find_paragraph(doc.paragraphs, element)
                if para is not None:
                    md = self._convert_paragraph(para, doc, max_width)
                    if md:
                        md_lines.append(md)
            elif tag == 'tbl':
                table = self._find_table(doc.tables, element)
                if table is not None:
                    md = self._convert_table(table, doc, max_width)
                    if md:
                        md_lines.append(md)

        return '\n\n'.join(md_lines)

    @staticmethod
    def _find_paragraph(paragraphs, element):
        for p in paragraphs:
            if p._element is element:
                return p
        return None

    @staticmethod
    def _find_table(tables, element):
        for t in tables:
            if t._element is element:
                return t
        return None

    def _convert_paragraph(self, para, doc, max_width: int) -> str | None:
        text = para.text.strip()
        if not text:
            return None

        style_name = para.style.name if para.style else ''

        # Heading
        if style_name.startswith('Heading'):
            try:
                level = int(style_name.split()[-1])
            except (IndexError, ValueError):
                level = 1
            level = max(1, min(6, level))
            return f"{'#' * level} {text}"

        # List detection via numbering properties
        pPr = para._element.find(qn('w:pPr'))
        if pPr is not None:
            numPr = pPr.find(qn('w:numPr'))
            if numPr is not None:
                numId = numPr.find(qn('w:numId'))
                if numId is not None and numId.get(qn('w:val')) != '0':
                    return f"- {text}"

        # Inline images
        image_mds = []
        for run in para.runs:
            for img in run._element.findall(qn('w:drawing')):
                blip = img.find('.//' + qn('a:blip'))
                if blip is not None:
                    embed_id = blip.get(qn('r:embed'))
                    if embed_id is not None:
                        try:
                            image_part = doc.part.related_parts[embed_id]
                            b64 = image_to_base64(image_part.blob, max_width, 'docx-image')
                            if b64:
                                image_mds.append(b64)
                        except (KeyError, Exception):
                            pass

        if image_mds:
            return '\n\n'.join(image_mds)

        # Inline formatting
        result = self._format_runs(para)
        return result if result.strip() else None

    @staticmethod
    def _format_runs(para) -> str:
        """Build Markdown string from paragraph runs, preserving bold/italic/underline."""
        result = ''
        for run in para.runs:
            t = run.text
            if not t:
                continue
            if run.bold and run.italic:
                t = f'***{t}***'
            elif run.bold:
                t = f'**{t}**'
            elif run.italic:
                t = f'*{t}*'
            if run.underline:
                t = f'<u>{t}</u>'
            result += t
        return result

    def _convert_table(self, table: Table, doc, max_width: int) -> str:
        """Convert a Word table to Markdown."""
        if not table.rows:
            return ''
        rows = [
            [cell.text.replace('\n', ' ').replace('|', '\\|') for cell in row.cells]
            for row in table.rows
        ]
        return rows_to_markdown_table(rows)
