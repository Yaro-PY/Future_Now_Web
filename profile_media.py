"""Small private avatars stored in the existing shared PostgreSQL database."""
import asyncio
import io
import threading
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, select, update
import database as db
from web_auth import AuthError

MAX_UPLOAD = 2 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_STORED = 256 * 1024
IMAGE_SLOTS = threading.BoundedSemaphore(2)


def prepare_image(data):
    if not data or len(data) > MAX_UPLOAD: raise AuthError('avatar_size', 413)
    try:
        with IMAGE_SLOTS, warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=['JPEG', 'PNG', 'WEBP']) as image:
                if image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    raise AuthError('avatar_invalid', 422)
                image.load()
                image = ImageOps.exif_transpose(image)
                if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                    rgba = image.convert('RGBA')
                    background = Image.new('RGBA', rgba.size, 'white')
                    background.alpha_composite(rgba)
                    image = background.convert('RGB')
                else: image = image.convert('RGB')
                image = ImageOps.fit(image, (512, 512), method=Image.Resampling.LANCZOS)
                output = io.BytesIO()
                image.save(output, format='WEBP', quality=82, method=4)
                result = output.getvalue()
                if len(result) > MAX_STORED: raise AuthError('avatar_size', 413)
                return result
    except AuthError: raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AuthError('avatar_invalid', 422) from None


async def save_avatar(account_id, data):
    content = await asyncio.to_thread(prepare_image, data)
    async with db.Session() as session:
        account = await session.scalar(select(db.Account).where(db.Account.telegram_id == account_id).with_for_update())
        if not account: raise AuthError('authentication_required', 401)
        stmt = db.insert_for(db.Avatar).values(account_id=account_id, content=content, updated_at=db.utcnow())
        await session.execute(stmt.on_conflict_do_update(index_elements=['account_id'], set_={
            'content': content, 'updated_at': db.utcnow()}))
        await session.execute(update(db.Account).where(db.Account.telegram_id == account_id).values(
            avatar_revision=db.Account.avatar_revision + 1))
        await session.commit()


async def remove_avatar(account_id):
    async with db.Session() as session:
        await session.execute(delete(db.Avatar).where(db.Avatar.account_id == account_id))
        await session.execute(update(db.Account).where(db.Account.telegram_id == account_id).values(avatar_revision=0))
        await session.commit()


async def avatar_content(account_id):
    async with db.Session() as session:
        return await session.scalar(select(db.Avatar.content).where(db.Avatar.account_id == account_id))
