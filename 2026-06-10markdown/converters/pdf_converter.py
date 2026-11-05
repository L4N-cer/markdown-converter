"""PDF to Markdown converter using PyMuPDF."""

import fitz

from converters.base import AbstractConverter
from utils.image_utils import image_to_base64
from utils.table_utils import rows_to_markdown_table


class PdfConverter(AbstractConverter):
    """Convert PDF files to Markdown."""

    def convert(self, file_path: str, options: dict | None = None) -> str:
        options = options or {}
        max_width = options.get('max_image_width', 800)
        page_breaks = options.get('pdf_page_breaks', True)

        doc = fitz.open(file_path)
        try:
            md_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_lines = []

                # Extract text blocks sorted by position
                blocks = page.get_text('dict')['blocks']
                text_blocks = [b for b in blocks if b['type'] == 0]
                text_blocks.sort(key=lambda b: (round(b['bbox'][1] / 10) * 10, b['bbox'][0]))

                # Detect largest font size for heading heuristic
                all_spans = []
                for block in text_blocks:
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            all_spans.append(span)
                max_font = max((s['size'] for s in all_spans), default=12)

                for block in text_blocks:
                    line_texts = []
                    for line in block.get('lines', []):
                        line_text = ''.join(span['text'] for span in line['spans'])
                        if not line_text.strip():
                            continue
                        avg_size = sum(s['size'] for s in line['spans']) / max(1, len(line['spans']))
                        if avg_size >= max_font * 0.9:
                            line_text = f'# {line_text.strip()}'
                        elif avg_size >= max_font * 0.75:
                            line_text = f'## {line_text.strip()}'
                        elif avg_size >= max_font * 0.6:
                            line_text = f'### {line_text.strip()}'
                        line_texts.append(line_text)
                    if line_texts:
                        page_lines.append(' '.join(line_texts))

                # Extract tables
                try:
                    for table in page.find_tables():
                        try:
                            cells = table.extract()
                        except Exception:
                            continue
                        if cells:
                            cleaned = [
                                [str(c).replace('\n', ' ').replace('|', '\\|') if c else '' for c in row]
                                for row in cells
                            ]
                            table_md = rows_to_markdown_table(cleaned)
                            if table_md:
                                page_lines.append(table_md)
                except Exception:
                    pass

                # Extract images
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        b64 = image_to_base64(
                            base_image['image'], max_width, f'pdf-page{page_num + 1}-img'
                        )
                        if b64:
                            page_lines.append(b64)
                    except Exception:
                        pass

                if page_lines:
                    if page_num > 0 and page_breaks:
                        md_parts.append('\n---\n')
                    md_parts.append('\n\n'.join(page_lines))

            return '\n'.join(md_parts)
        finally:
            doc.close()
