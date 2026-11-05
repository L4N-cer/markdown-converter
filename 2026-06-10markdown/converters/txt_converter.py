"""Plain text to Markdown converter."""

import chardet

from converters.base import AbstractConverter


class TxtConverter(AbstractConverter):
    """Convert plain text files to Markdown."""

    def convert(self, file_path: str, options: dict | None = None) -> str:
        options = options or {}
        code_block_style = options.get('code_block_style', 'fenced')

        with open(file_path, 'rb') as f:
            raw = f.read()
        detected = chardet.detect(raw)
        encoding = detected['encoding'] or 'utf-8'

        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            text = raw.decode('utf-8', errors='replace')

        lines = text.split('\n')
        non_empty = [l for l in lines if l.strip()]

        # Heuristic: many blank-separated short paragraphs → prose mode
        blank_count = sum(1 for l in lines if l.strip() == '')
        total_lines = len(lines)
        if total_lines > 0 and blank_count / total_lines > 0.15 and len(non_empty) > 3:
            paragraphs = []
            current = []
            for line in lines:
                if line.strip():
                    current.append(line.strip())
                else:
                    if current:
                        paragraphs.append(' '.join(current))
                        current = []
            if current:
                paragraphs.append(' '.join(current))
            return '\n\n'.join(paragraphs)

        # Code block mode
        if code_block_style == 'fenced':
            return f'```text\n{text.rstrip()}\n```'
        else:
            return '\n'.join(f'    {line}' for line in lines)
