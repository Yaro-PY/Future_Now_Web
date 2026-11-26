"""Website direction cards and their catalog filters."""
from uuid import UUID, uuid4

from fastapi import Depends, Response
from pydantic import Field, SecretStr, field_validator
from sqlalchemy import select, update

from backend import database as db
from backend.event_media import decode_proposal_cover
from backend.flow_catalog import TOPICS, TYPES
from backend.web_schemas import Input


BUILTINS = tuple(key for key in TYPES if key != 'any')


class DirectionInput(Input):
    title_uk: str = Field(min_length=1, max_length=100)
    title_en: str = Field(default='', max_length=100)
    description_uk: str = Field(min_length=1, max_length=600)
    description_en: str = Field(default='', max_length=600)
    filter_type: str = 'any'
    topic: str | None = None
    cover_image: SecretStr | None = None

    @field_validator('title_uk', 'title_en', 'description_uk', 'description_en', mode='before')
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('filter_type', 'topic')
    @classmethod
    def catalog_key(cls, value, info):
        catalog = TYPES if info.field_name == 'filter_type' else TOPICS
        if value is not None and value not in catalog:
            raise ValueError('Unknown option')
        return value


class DirectionEdit(DirectionInput):
    expected_revision: int = Field(ge=0, lt=2147483647)


def direction_out(key, row=None):
    result = dict(row) if row is not None else dict(
        key=key, title_uk=TYPES[key][0], title_en=TYPES[key][1], description_uk='', description_en='',
        filter_type=key, topic=None, revision=0, cover_version=None)
    version = result.pop('cover_version')
    result['cover_url'] = f'/api/v1/directions/{key}/cover/{version}' if version else None
    result['default_cover_url'] = (f'/assets/images/directions/{key}.jpg' if key in BUILTINS
                                   else '/assets/images/community.jpg')
    return result


async def direction_values(body, account_id):
    values = body.model_dump(exclude={'cover_image', 'expected_revision'})
    if 'cover_image' in body.model_fields_set:
        content = await decode_proposal_cover(body.cover_image, account_id)
        values.update(cover_content=content, cover_version=uuid4().hex if content is not None else None)
    return values


def install(router, *, changing_user, require_admin, fail):
    table = db.directions
    cards = select(
        table.c.key, table.c.title_uk, table.c.title_en, table.c.description_uk,
        table.c.description_en, table.c.filter_type, table.c.topic, table.c.revision,
        table.c.cover_version,
    ).order_by(table.c.created_at, table.c.key)

    async def persist(key, values, revision):
        async with db.Session() as session:
            if revision == 0:
                query = db.insert_for(table).values(key=key, **values, revision=1)
                query = query.on_conflict_do_nothing(index_elements=[table.c.key])
            else:
                query = update(table).where(table.c.key == key, table.c.revision == revision)
                query = query.values(**values, revision=revision + 1)
            result = await session.execute(query)
            if result.rowcount != 1:
                exists = await session.scalar(select(table.c.key).where(table.c.key == key))
                if not exists and key not in BUILTINS:
                    fail('not_found', 404)
                fail('edit_conflict', 409)
            row = (await session.execute(cards.where(table.c.key == key))).mappings().one()
            await session.commit()
        return direction_out(key, row)

    @router.get('/directions', tags=['Directions'])
    async def list_directions():
        async with db.Session() as session:
            rows = (await session.execute(cards)).mappings()
            saved = {row['key']: row for row in rows}
        return {'items': [direction_out(key, saved.pop(key, None)) for key in BUILTINS] +
                [direction_out(key, row) for key, row in saved.items()]}

    @router.get('/directions/{key}/cover/{version}', tags=['Directions'])
    async def cover(key: str, version: UUID):
        async with db.Session() as session:
            content = await session.scalar(select(table.c.cover_content).where(
                table.c.key == key, table.c.cover_version == version.hex))
        if content is None:
            fail('not_found', 404)
        return Response(content, media_type='image/webp')

    @router.post('/admin/directions', status_code=201, tags=['Administration'])
    async def create(body: DirectionInput, user=Depends(changing_user)):
        require_admin(user)
        values = await direction_values(body, user.account.telegram_id)
        return await persist(uuid4().hex, values, 0)

    @router.patch('/admin/directions/{key}', tags=['Administration'])
    async def edit(key: str, body: DirectionEdit, user=Depends(changing_user)):
        require_admin(user)
        if len(key) > 32 or (body.expected_revision == 0 and key not in BUILTINS):
            fail('not_found', 404)
        values = await direction_values(body, user.account.telegram_id)
        return await persist(key, values, body.expected_revision)
