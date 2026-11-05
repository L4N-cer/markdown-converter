"""Shared utility for converting rows to Markdown pipe tables."""


def rows_to_markdown_table(rows: list[list[str]]) -> str:
    """Convert a list of cell-string rows to a Markdown pipe table.

    Args:
        rows: List of rows, each row is a list of cell strings.

    Returns:
        Markdown pipe table string, or empty string if rows is empty.
    """
    if not rows:
        return ''

    md_rows = []
    for i, row in enumerate(rows):
        cleaned = [c.replace('\n', ' ').replace('|', '\\|') for c in row]
        md_rows.append('| ' + ' | '.join(cleaned) + ' |')
        if i == 0:
            md_rows.append('| ' + ' | '.join(['---'] * len(cleaned)) + ' |')

    return '\n'.join(md_rows)
