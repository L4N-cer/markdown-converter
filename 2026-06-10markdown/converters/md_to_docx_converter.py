"""Markdown (.md) to Word (.docx) converter."""

import base64
import io
import os
import re
import tempfile

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

# Match inline Base64 images: ![alt](data:image/xxx;base64,YYY)
RE_BASE64_IMG = re.compile(r'!\[([^\]]*)\]\(data:image/\w+;base64,([^\)]+)\)')
# Match regular images: ![alt](url)
RE_IMG = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')
# Match links: [text](url)
RE_LINK = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
# Match inline code: `code`
RE_CODE = re.compile(r'`([^`]+)`')
# Match bold+italic: ***text***
RE_BOLD_ITALIC = re.compile(r'\*\*\*(.+?)\*\*\*')
# Match bold: **text**
RE_BOLD = re.compile(r'\*\*(.+?)\*\*')
# Match italic: *text*
RE_ITALIC = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')
# Match strikethrough: ~~text~~
RE_STRIKE = re.compile(r'~~(.+?)~~')


class MdToDocxConverter:
    """Convert Markdown to .docx Word document (compatible with ConvertWorker interface)."""

    IMAGE_MAX_INCHES = 5.5

    # ─── Worker-compatible interface: convert(file_path, options) → str ──────

    def convert(self, file_path: str, options: dict | None = None) -> str:
        """Read a .md file and convert to .docx. Returns the output file path.

        This matches the AbstractConverter interface so ConvertWorker can use it.
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            markdown_text = f.read()

        # Generate output path next to source file
        base = os.path.splitext(os.path.basename(file_path))[0]
        out_dir = os.path.dirname(os.path.abspath(file_path))
        output_path = os.path.join(out_dir, f'{base}.docx')

        self._build_docx(markdown_text, output_path, options or {})
        return output_path

    # ─── String-based interface for preview/editor content ──────────────────

    def convert_text(self, markdown_text: str, output_path: str, options: dict | None = None):
        """Convert a Markdown string and save to the given output_path."""
        self._build_docx(markdown_text, output_path, options or {})

    # ─── Internal ───────────────────────────────────────────────────────────

    def _build_docx(self, markdown_text: str, output_path: str, options: dict):
        """Build a .docx from markdown text and save to output_path."""
        doc = Document()

        style = doc.styles['Normal']
        style.font.name = 'Calibri'
        style.font.size = Pt(11)

        lines = markdown_text.split('\n')
        i = 0
        while i < len(lines):
            i = self._process_block(doc, lines, i)
            i += 1

        doc.save(output_path)

    def _process_block(self, doc: Document, lines: list[str], i: int) -> int:
        """Process one block-level element starting at line i. Returns the last consumed index."""
        line = lines[i]

        # Blank line
        if not line.strip():
            return i

        # Heading: # text
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            p = doc.add_heading(text, level=min(level, 9))
            return i

        # Horizontal rule: --- or *** or ___
        if re.match(r'^(\-{3,}|\*{3,}|_{3,})\s*$', line):
            doc.add_paragraph('_' * 50)
            return i

        # Fenced code block: ```lang ... ```
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code_text = '\n'.join(code_lines)
            p = doc.add_paragraph()
            run = p.add_run(code_text)
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            return i

        # Table: | col1 | col2 |
        if '|' in line and line.strip().startswith('|'):
            return self._process_table(doc, lines, i)

        # Unordered list: - item
        if re.match(r'^[\-\*\+]\s+', line):
            return self._process_list(doc, lines, i, bullet=True)

        # Ordered list: 1. item
        if re.match(r'^\d+\.\s+', line):
            return self._process_list(doc, lines, i, bullet=False)

        # Blockquote: > text
        if line.strip().startswith('> '):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('> '):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            i -= 1
            for ql in quote_lines:
                p = doc.add_paragraph(ql)
                p.paragraph_format.left_indent = Inches(0.5)
                pf = p.paragraph_format
                pf.space_before = Pt(2)
                pf.space_after = Pt(2)
            return i

        # Regular paragraph (may contain inline formatting)
        text = self._format_inline(doc.add_paragraph(), line)
        return i

    def _process_table(self, doc: Document, lines: list[str], i: int) -> int:
        """Consume a Markdown pipe table."""
        rows_raw = []
        while i < len(lines) and '|' in lines[i]:
            rows_raw.append(lines[i])
            i += 1
        i -= 1

        # Parse rows
        parsed = []
        for row_str in rows_raw:
            if re.match(r'^[\|\s\-:]+$', row_str):  # separator row
                continue
            cells = [c.strip() for c in row_str.strip().strip('|').split('|')]
            parsed.append(cells)

        if not parsed:
            return i

        table = doc.add_table(rows=len(parsed), cols=len(parsed[0]))
        table.style = 'Light Grid Accent 1'
        for ri, row_cells in enumerate(parsed):
            for ci, cell_text in enumerate(row_cells):
                if ci < len(parsed[0]):
                    cell = table.cell(ri, ci)
                    cell.text = ''
                    p = cell.paragraphs[0]
                    self._format_inline(p, cell_text)

        doc.add_paragraph()  # spacing
        return i

    def _process_list(self, doc: Document, lines: list[str], i: int, bullet: bool) -> int:
        """Consume a Markdown list."""
        items = []
        prefix_pattern = r'^[\-\*\+]\s+' if bullet else r'^\d+\.\s+'
        while i < len(lines) and re.match(prefix_pattern, lines[i]):
            item_text = re.sub(prefix_pattern, '', lines[i], count=1)
            items.append(item_text)
            i += 1
        i -= 1

        for item in items:
            p = doc.add_paragraph(style='List Bullet' if bullet else 'List Number')
            p.clear()
            self._format_inline(p, item)

        return i

    def _format_inline(self, p, text: str):
        """Apply inline Markdown formatting to a paragraph. Returns nothing (modifies p in-place)."""
        # Remove <u>/</u> tags (convert to underline)
        text = text.replace('<u>', '\x00u\x00').replace('</u>', '\x00/u\x00')

        # Split into segments: normal text, images, and <u> regions
        # First handle images (they become separate runs)
        # Process: bold-italic → bold → italic → strikethrough → code → links
        self._add_formatted_text(p, text)
        return p

    def _add_formatted_text(self, p, text: str):
        """Recursively apply inline formatting to a paragraph."""
        if not text:
            return

        # Check for images at the start
        m = RE_BASE64_IMG.match(text)
        if m:
            alt = m.group(1)
            b64_data = m.group(2)
            try:
                img_bytes = base64.b64decode(b64_data)
                img = Image.open(io.BytesIO(img_bytes))
                w, h = img.size
                max_w = Inches(self.IMAGE_MAX_INCHES)
                if w > max_w.inches * 300 or True:  # approximate DPI
                    ratio = min(max_w.inches * 96 / w, 1.0)
                    w, h = int(w * ratio), int(h * ratio)
                run = p.add_run()
                img_stream = io.BytesIO()
                img.save(img_stream, format='PNG')
                img_stream.seek(0)
                run.add_picture(img_stream, width=Inches(min(w / 96, self.IMAGE_MAX_INCHES)))
                p.add_run('\n')
            except Exception:
                p.add_run(f'[{alt}]')
            self._add_formatted_text(p, text[m.end():])
            return

        m = RE_IMG.match(text)
        if m:
            alt = m.group(1)
            url = m.group(2)
            p.add_run(f'[Image: {alt}] ({url})')
            self._add_formatted_text(p, text[m.end():])
            return

        # Bold + Italic
        m = RE_BOLD_ITALIC.search(text)
        if m:
            self._add_formatted_text(p, text[:m.start()])
            run = p.add_run(m.group(1))
            run.bold = True
            run.italic = True
            self._add_formatted_text(p, text[m.end():])
            return

        # Bold
        m = RE_BOLD.search(text)
        if m:
            self._add_formatted_text(p, text[:m.start()])
            run = p.add_run(m.group(1))
            run.bold = True
            self._add_formatted_text(p, text[m.end():])
            return

        # Italic
        m = RE_ITALIC.search(text)
        if m:
            self._add_formatted_text(p, text[:m.start()])
            run = p.add_run(m.group(1))
            run.italic = True
            self._add_formatted_text(p, text[m.end():])
            return

        # Strikethrough
        m = RE_STRIKE.search(text)
        if m:
            self._add_formatted_text(p, text[:m.start()])
            run = p.add_run(m.group(1))
            run.font.strike = True
            self._add_formatted_text(p, text[m.end():])
            return

        # Inline code
        m = RE_CODE.search(text)
        if m:
            self._add_formatted_text(p, text[:m.start()])
            run = p.add_run(m.group(1))
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
            self._add_formatted_text(p, text[m.end():])
            return

        # Link
        m = RE_LINK.search(text)
        if m:
            self._add_formatted_text(p, text[:m.start()])
            run = p.add_run(m.group(1))
            run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
            run.underline = True
            self._add_formatted_text(p, text[m.end():])
            return

        # Underline tags
        u_start = text.find('\x00u\x00')
        if u_start >= 0:
            self._add_formatted_text(p, text[:u_start])
            u_end = text.find('\x00/u\x00', u_start + 4)
            if u_end >= 0:
                run = p.add_run(text[u_start + 4:u_end])
                run.underline = True
                self._add_formatted_text(p, text[u_end + 5:])
            else:
                p.add_run(text[u_start:])
            return

        # Plain text — add remaining
        p.add_run(text)
