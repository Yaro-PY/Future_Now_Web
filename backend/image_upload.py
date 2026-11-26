"""Validation and normalization for website image uploads."""
import io
import threading
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from backend.web_auth import AuthError

IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')
MAX_UPLOAD = 2 * 1024 * 1024
MAX_PIXELS = 16_000_000
IMAGE_SLOTS = threading.BoundedSemaphore(2)


async def read_image_upload(request, *, invalid, too_large):
    if request.headers.get('content-type', '').split(';')[0] not in IMAGE_TYPES:
        raise AuthError(invalid, 415)
    try:
        size = int(request.headers.get('content-length', '0'))
    except ValueError:
        raise AuthError(invalid, 422) from None
    if size > MAX_UPLOAD:
        raise AuthError(too_large, 413)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_UPLOAD:
            raise AuthError(too_large, 413)
        data.extend(chunk)
    return bytes(data)


def encode_webp(data, *, size, crop, max_stored, qualities, invalid, too_large):
    if not data or len(data) > MAX_UPLOAD:
        raise AuthError(too_large, 413)
    try:
        with IMAGE_SLOTS, warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=['JPEG', 'PNG', 'WEBP']) as image:
                if image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    raise AuthError(invalid, 422)
                image = ImageOps.exif_transpose(image)
                if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                    rgba = image.convert('RGBA')
                    background = Image.new('RGBA', rgba.size, 'white')
                    background.alpha_composite(rgba)
                    image = background.convert('RGB')
                else:
                    image = image.convert('RGB')
                if crop:
                    image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
                else:
                    image.thumbnail(size, Image.Resampling.LANCZOS)
                for quality in qualities:
                    output = io.BytesIO()
                    image.save(output, format='WEBP', quality=quality, method=4)
                    if output.tell() <= max_stored:
                        return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AuthError(invalid, 422) from None
    raise AuthError(too_large, 413)
