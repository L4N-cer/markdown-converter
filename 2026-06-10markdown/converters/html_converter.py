"""HTML to Markdown converter using BeautifulSoup."""

import os
import re

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from converters.base import AbstractConverter
from utils.image_utils import image_to_base64
from utils.table_utils import rows_to_markdown_table

SKIP_TAGS = {'script', 'style', 'noscript', 'meta', 'link', 'head'}

BLOCK_TAGS = {
    'p', 'div', 'section', 'article', 'header', 'footer', 'main', 'aside', 'nav',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'table', 'pre',
    'blockquote', 'hr', 'figure', 'figcaption', 'form', 'fieldset',
}

HEADING_PATTERN = re.compile(r'^h([1-6])$')


class HtmlConverter(AbstractConverter):
    """Convert HTML files to Markdown."""

    def convert(self, file_path: str, options: dict | None = None) -> str:
        options = options or {}
        max_width = options.get('max_image_width', 800)
        code_style = options.get('code_block_style', 'fenced')

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')
        body = soup.find('body') or soup
        base_dir = os.path.dirname(os.path.abspath(file_path))
        md_lines = []

        for child in body.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text:
                    md_lines.append(text)
            elif isinstance(child, Tag):
                md = self._convert_tag(child, base_dir, max_width, code_style)
                if md:
                    md_lines.append(md)

        return '\n\n'.join(md_lines)

    def _convert_tag(self, tag: Tag, base_dir: str, max_width: int, code_style: str) -> str | None:
        tag_name = tag.name.lower() if tag.name else ''
        if tag_name in SKIP_TAGS:
            return None

        # Headings
        m = HEADING_PATTERN.match(tag_name)
        if m:
            level = int(m.group(1))
            text = self._get_text(tag)
            return f"{'#' * level} {text.strip()}" if text.strip() else None

        # Paragraph
        if tag_name == 'p':
            return self._convert_inline(tag, base_dir, max_width)

        # Lists
        if tag_name in ('ul', 'ol'):
            items = []
            for idx, li in enumerate(tag.find_all('li', recursive=False), start=1):
                item_text = self._convert_inline(li, base_dir, max_width)
                prefix = '- ' if tag_name == 'ul' else f'{idx}. '
                items.append(f'{prefix}{item_text}')
            return '\n'.join(items) if items else None

        # Blockquote
        if tag_name == 'blockquote':
            text = self._get_text(tag)
            return '\n'.join(f'> {line}' for line in text.strip().split('\n'))

        # Pre / Code
        if tag_name == 'pre':
            code_tag = tag.find('code')
            lang = ''
            if code_tag:
                classes = code_tag.get('class', [])
                for cls in classes:
                    if cls.startswith('language-') or cls.startswith('lang-'):
                        lang = cls.split('-', 1)[1]
                        break
                text = code_tag.get_text()
            else:
                text = tag.get_text()

            if code_style == 'fenced':
                return f'```{lang}\n{text.rstrip()}\n```'
            else:
                return '\n'.join(f'    {line}' for line in text.split('\n'))

        # Horizontal rule
        if tag_name == 'hr':
            return '---'

        # Table
        if tag_name == 'table':
            return self._table_to_markdown(tag)

        # Standalone image
        if tag_name == 'img':
            return self._img_to_markdown(tag, base_dir, max_width)

        # Standalone link
        if tag_name == 'a':
            href = tag.get('href', '')
            text = tag.get_text(strip=True) or href
            return f'[{text}]({href})'

        # Generic block: recurse children
        if tag_name in BLOCK_TAGS:
            parts = []
            for child in tag.children:
                if isinstance(child, NavigableString):
                    text = child.strip()
                    if text:
                        parts.append(text)
                elif isinstance(child, Tag):
                    md = self._convert_tag(child, base_dir, max_width, code_style)
                    if md:
                        parts.append(md)
            return '\n\n'.join(parts) if parts else None

        # Fallback: inline
        return self._convert_inline(tag, base_dir, max_width)

    def _convert_inline(self, tag: Tag, base_dir: str, max_width: int) -> str:
        """Convert inline HTML content to Markdown."""
        result = ''
        for child in tag.children:
            if isinstance(child, NavigableString):
                result += child
            elif isinstance(child, Tag):
                name = child.name.lower() if child.name else ''
                inner = self._convert_inline(child, base_dir, max_width)
                if name in ('strong', 'b'):
                    result += f'**{inner}**'
                elif name in ('em', 'i'):
                    result += f'*{inner}*'
                elif name == 'a':
                    href = child.get('href', '')
                    result += f'[{inner}]({href})'
                elif name == 'img':
                    result += (self._img_to_markdown(child, base_dir, max_width) or '')
                elif name == 'code':
                    result += f'`{inner}`'
                elif name == 'br':
                    result += '  \n'
                elif name == 'u':
                    result += f'<u>{inner}</u>'
                elif name in ('del', 's'):
                    result += f'~~{inner}~~'
                else:
                    result += inner
        return result

    @staticmethod
    def _get_text(tag: Tag) -> str:
        return tag.get_text('\n', strip=True)

    def _img_to_markdown(self, tag: Tag, base_dir: str, max_width: int) -> str | None:
        """Convert <img> to Base64 Markdown image."""
        src = tag.get('src', '')
        alt = tag.get('alt', 'image')
        if not src:
            return None
        if src.startswith('data:'):
            return f'![{alt}]({src})'

        img_bytes = None

        # Local file
        if not src.startswith(('http://', 'https://', '//')):
            img_path = src if os.path.isabs(src) else os.path.join(base_dir, src)
            if os.path.isfile(img_path):
                try:
                    with open(img_path, 'rb') as f:
                        img_bytes = f.read()
                except Exception:
                    pass

        # Remote URL
        if img_bytes is None and src.startswith(('http://', 'https://', '//')):
            if src.startswith('//'):
                src = 'https:' + src
            try:
                resp = requests.get(src, timeout=10)
                resp.raise_for_status()
                img_bytes = resp.content
            except Exception:
                return f'![{alt}]({src})'

        if img_bytes:
            b64 = image_to_base64(img_bytes, max_width, alt)
            if b64:
                return b64

        return f'![{alt}]({src})'

    def _table_to_markdown(self, table: Tag) -> str:
        """Convert HTML <table> to Markdown."""
        rows = table.find_all('tr')
        if not rows:
            return ''

        parsed = []
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                parsed.append([
                    self._get_text(cell).replace('\n', ' ').replace('|', '\\|')
                    for cell in cells
                ])

        return rows_to_markdown_table(parsed)
