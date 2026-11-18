"""Small private avatars stored in the existing shared PostgreSQL database."""
import asyncio

from sqlalchemy import delete, select, update
import database as db
from image_upload import encode_webp
from web_auth import AuthError


def prepare_image(data):
    return encode_webp(data, size=(512, 512), crop=True, max_stored=256 * 1024, qualities=(82,),
                       invalid='avatar_invalid', too_large='avatar_size')


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
