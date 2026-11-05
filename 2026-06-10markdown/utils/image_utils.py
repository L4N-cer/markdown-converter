"""Image processing utilities — resize and Base64-encode images."""

import base64
import io
from typing import Optional

from PIL import Image

MIME_MAP = {
    'JPEG': 'image/jpeg',
    'PNG':  'image/png',
    'GIF':  'image/gif',
    'BMP':  'image/bmp',
    'WEBP': 'image/webp',
    'TIFF': 'image/tiff',
}


def image_to_base64(
    image_data: bytes,
    max_width: int = 800,
    alt_text: str = 'image',
) -> Optional[str]:
    """Convert raw image bytes to a Base64 Markdown image string."""
    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception:
        return None

    # Resize if wider than max_width
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # Convert fully opaque RGBA to RGB to save space
    if img.mode == 'RGBA':
        alpha = img.getchannel('A')
        if alpha.getextrema()[0] == 255:
            img = img.convert('RGB')

    # Output format: JPEG for RGB, PNG for others (RGBA, palette)
    if img.mode in ('RGBA', 'P'):
        save_format = 'PNG'
    else:
        save_format = 'JPEG'

    mime = MIME_MAP.get(save_format, 'image/png')

    buf = io.BytesIO()
    if save_format == 'JPEG':
        img.save(buf, format='JPEG', quality=85)
    else:
        img.save(buf, format='PNG')

    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'![{alt_text}](data:{mime};base64,{b64})'
