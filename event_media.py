"""Public course covers stored separately from source-managed event data."""
import asyncio
from uuid import UUID, uuid4

from fastapi import Depends, Request, Response
from sqlalchemy import delete, select

import database as db
from image_upload import encode_webp, read_image_upload
from web_auth import reserve_attempt


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


def install(router, *, changing_user, require_admin, fail):
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
