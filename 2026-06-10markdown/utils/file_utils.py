"""File format detection and utility functions."""

from pathlib import Path

EXTENSION_MAP = {
    '.docx': 'Word 文档',
    '.pdf':  'PDF 文档',
    '.pptx': 'PowerPoint 演示文稿',
    '.html': 'HTML 文件',
    '.htm':  'HTML 文件',
    '.txt':  '纯文本文件',
    '.md':   'Markdown 文件',
}

SUPPORTED_EXTENSIONS = set(EXTENSION_MAP.keys())

# Extensions that convert TO markdown
TO_MARKDOWN_EXTENSIONS = {'.docx', '.pdf', '.pptx', '.html', '.htm', '.txt'}

# Extensions that convert FROM markdown (reverse direction)
FROM_MARKDOWN_EXTENSIONS = {'.md'}

HTML_SIGNATURES = [
    b'<!DOCTYPE html',
    b'<html',
    b'<HTML',
]


def detect_format(file_path: str) -> str | None:
    """Detect the format of a file.

    Returns a human-readable format name, or None if unsupported.
    """
    ext = Path(file_path).suffix.lower()

    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    # Content sniffing for HTML files with wrong extension
    try:
        with open(file_path, 'rb') as f:
            head = f.read(256)
        for sig in HTML_SIGNATURES:
            if sig in head:
                return 'HTML 文件'
    except (OSError, IOError):
        pass

    return None


def get_file_info(file_path: str) -> dict:
    """Get basic info about a file.

    Returns dict with keys: name, size_bytes, size_display, format, extension, direction.
    direction is 'to_markdown', 'from_markdown', or None.
    """
    path = Path(file_path)
    size = path.stat().st_size

    if size < 1024:
        size_display = f"{size} B"
    elif size < 1024 * 1024:
        size_display = f"{size / 1024:.1f} KB"
    else:
        size_display = f"{size / (1024 * 1024):.1f} MB"

    ext = path.suffix.lower()
    direction = None
    if ext in TO_MARKDOWN_EXTENSIONS:
        direction = 'to_markdown'
    elif ext in FROM_MARKDOWN_EXTENSIONS:
        direction = 'from_markdown'

    return {
        'name': path.name,
        'size_bytes': size,
        'size_display': size_display,
        'format': detect_format(file_path),
        'extension': ext,
        'direction': direction,
    }
