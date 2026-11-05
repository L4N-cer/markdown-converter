"""Abstract base converter and factory function."""

from abc import ABC, abstractmethod
from pathlib import Path


class AbstractConverter(ABC):
    """Base class for all file-to-markdown converters."""

    @abstractmethod
    def convert(self, file_path: str, options: dict | None = None) -> str:
        """Convert a file to Markdown.

        Args:
            file_path: Absolute path to the source file.
            options: Optional dict with keys like 'max_image_width', 'code_block_style'.

        Returns:
            Markdown string.
        """
        ...


def get_converter(file_path: str):
    """Return the appropriate converter for the given file.

    Raises ValueError if the file format is not supported.
    """
    from utils.file_utils import detect_format, get_file_info

    fmt = detect_format(file_path)

    if fmt == 'Word 文档':
        from converters.docx_converter import DocxConverter
        return DocxConverter()
    elif fmt == 'PDF 文档':
        from converters.pdf_converter import PdfConverter
        return PdfConverter()
    elif fmt == 'PowerPoint 演示文稿':
        from converters.pptx_converter import PptxConverter
        return PptxConverter()
    elif fmt == 'HTML 文件':
        from converters.html_converter import HtmlConverter
        return HtmlConverter()
    elif fmt == '纯文本文件':
        from converters.txt_converter import TxtConverter
        return TxtConverter()
    else:
        ext = Path(file_path).suffix.lower()
        raise ValueError(f"不支持的文件格式: {ext}")
