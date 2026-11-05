"""PowerPoint (.pptx) to Markdown converter."""

from pptx import Presentation
from pptx.shapes.base import BaseShape

from converters.base import AbstractConverter
from utils.image_utils import image_to_base64
from utils.table_utils import rows_to_markdown_table


class PptxConverter(AbstractConverter):
    """Convert PowerPoint .pptx files to Markdown."""

    def convert(self, file_path: str, options: dict | None = None) -> str:
        options = options or {}
        max_width = options.get('max_image_width', 800)

        prs = Presentation(file_path)
        md_parts = []

        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_lines = []

            title = f'## 幻灯片 {slide_num}'
            if slide.shapes.title and slide.shapes.title.text.strip():
                title = f'## 幻灯片 {slide_num}: {slide.shapes.title.text.strip()}'
            slide_lines.append(title)

            for shape in slide.shapes:
                md = self._convert_shape(shape, max_width)
                if md:
                    slide_lines.append(md)

            md_parts.append('\n\n'.join(slide_lines))
            md_parts.append('\n---\n')

        return '\n'.join(md_parts)

    def _convert_shape(self, shape: BaseShape, max_width: int) -> str | None:
        """Convert a single shape to Markdown."""
        if shape.has_table:
            rows = [
                [cell.text.replace('\n', ' ').replace('|', '\\|') for cell in row.cells]
                for row in shape.table.rows
            ]
            return rows_to_markdown_table(rows)

        # Picture
        if shape.shape_type == 13:
            try:
                return image_to_base64(shape.image.blob, max_width, 'ppt-image')
            except Exception:
                return None

        # Group shape — recurse
        if shape.shape_type == 6:
            group_lines = []
            for child in shape.shapes:
                child_md = self._convert_shape(child, max_width)
                if child_md:
                    group_lines.append(child_md)
            return '\n\n'.join(group_lines) if group_lines else None

        # Text frame
        if shape.has_text_frame:
            return self._convert_text_frame(shape)

        return None

    def _convert_text_frame(self, shape) -> str | None:
        """Convert a text frame to Markdown."""
        tf = shape.text_frame
        paragraphs = []
        for para in tf.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            is_heading = False
            for run in para.runs:
                if run.font.size is not None:
                    size_pt = run.font.size / 12700  # EMU → points
                    if size_pt >= 28:
                        text = f'### {text}'
                        is_heading = True
                    elif size_pt >= 20:
                        text = f'#### {text}'
                        is_heading = True
                    break

            if not is_heading:
                formatted = ''
                for run in para.runs:
                    t = run.text
                    if not t:
                        continue
                    if run.font.bold and run.font.italic:
                        t = f'***{t}***'
                    elif run.font.bold:
                        t = f'**{t}**'
                    elif run.font.italic:
                        t = f'*{t}*'
                    formatted += t
                text = formatted if formatted.strip() else text

            paragraphs.append(text)

        return '\n\n'.join(paragraphs) if paragraphs else None
