"""Public course covers stored separately from source-managed event data."""
import asyncio
from base64 import b64decode
from binascii import Error as Base64Error
from uuid import UUID, uuid4

from fastapi import Depends, Request, Response
from sqlalchemy import delete, select

from backend import database as db
from backend.image_upload import MAX_UPLOAD, encode_webp, read_image_upload
from backend.web_auth import AuthError, reserve_attempt


def cover_url(event_id, version):
    return f'/api/v1/opportunities/{event_id}/cover/{version}' if version else None


async def cover_urls(event_ids):
    if not event_ids:
        return {}
    async with db.Session() as session:
        rows = await session.execute(select(db.event_covers.c.event_id, db.event_covers.c.version)
                                     .where(db.event_covers.c.event_id.in_(event_ids)))
        return {event_id: cover_url(event_id, version) for event_id, version in rows}


def prepare_cover(data):
    return encode_webp(data, size=(1440, 900), crop=False, max_stored=512 * 1024,
                       qualities=(84, 72, 60), invalid='cover_invalid', too_large='cover_size')


async def proposal_cover_urls(submission_ids):
    if not submission_ids:
        return {}
    covers = db.submission_covers.c
    async with db.Session() as session:
        rows = await session.execute(select(covers.submission_id, covers.version)
                                     .where(covers.submission_id.in_(submission_ids)))
        return {item_id: f'/api/v1/proposals/{item_id}/cover/{version}' for item_id, version in rows}


async def decode_proposal_cover(value, account_id):
    if value is None:
        return None
    encoded = value.get_secret_value()
    if len(encoded) > 4 * ((MAX_UPLOAD + 2) // 3):
        raise AuthError('cover_size', 413)
    await reserve_attempt(f'proposal-cover:{account_id}', 20)
    try:
        original = b64decode(encoded, validate=True)
    except (Base64Error, ValueError):
        raise AuthError('cover_invalid', 422) from None
    return await asyncio.to_thread(prepare_cover, original)


def install(router, *, current_user, changing_user, require_admin, fail):
    @router.get('/proposals/{submission_id}/cover/{version}', tags=['Proposals'])
    async def download_proposal_cover(submission_id: int, version: UUID, user=Depends(current_user)):
        if not 0 < submission_id <= 2147483647:
            fail('not_found', 404)
        covers = db.submission_covers.c
        async with db.Session() as session:
            query = select(covers.content).join(db.Submission, db.Submission.id == covers.submission_id).where(
                covers.submission_id == submission_id, covers.version == version.hex, db.Submission.status == 'pending')
            if not db.admin_user(user.account.telegram_id):
                query = query.where(db.Submission.telegram_id == user.account.telegram_id)
            content = await session.scalar(query)
        if content is None:
            fail('not_found', 404)
        return Response(content, media_type='image/webp', headers={
            'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

    @router.get('/opportunities/{event_id}/cover/{version}', tags=['Opportunities'])
    async def download(event_id: int, version: UUID):
        if not 0 < event_id <= 2147483647:
            fail('not_found', 404)
        async with db.Session() as session:
            content = await session.scalar(select(db.event_covers.c.content).where(
                db.event_covers.c.event_id == event_id, db.event_covers.c.version == version.hex))
        if content is None:
            fail('not_found', 404)
        return Response(content, media_type='image/webp', headers={
            'Cache-Control': 'public, max-age=300', 'X-Content-Type-Options': 'nosniff'})

    @router.put('/admin/opportunities/{event_id}/cover', tags=['Administration'])
    async def upload(event_id: int, request: Request, user=Depends(changing_user)):
        require_admin(user)
        if not 0 < event_id <= 2147483647 or not await db.get_event(event_id):
            fail('not_found', 404)
        await reserve_attempt(f'cover:{user.account.telegram_id}', 40)
        data = await read_image_upload(request, invalid='cover_invalid', too_large='cover_size')
        content = await asyncio.to_thread(prepare_cover, data)
        version = uuid4().hex
        async with db.Session() as session:
            stmt = db.insert_for(db.event_covers).values(event_id=event_id, version=version, content=content)
            await session.execute(stmt.on_conflict_do_update(index_elements=['event_id'],
                set_={'version': stmt.excluded.version, 'content': stmt.excluded.content}))
            await session.commit()
        return {'cover_url': cover_url(event_id, version)}

    @router.delete('/admin/opportunities/{event_id}/cover', status_code=204, tags=['Administration'])
    async def remove(event_id: int, user=Depends(changing_user)):
        require_admin(user)
        if not 0 < event_id <= 2147483647 or not await db.get_event(event_id):
            fail('not_found', 404)
        async with db.Session() as session:
            await session.execute(delete(db.event_covers).where(db.event_covers.c.event_id == event_id))
            await session.commit()
        return Response(status_code=204)
