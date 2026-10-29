import asyncio
import os
from datetime import timedelta
from sqlalchemy import select
import database as db
from catalog.providers import collect, PROVIDERS


def source_keys(value=None):
    keys = list(dict.fromkeys((value or os.getenv('CATALOG_SOURCES','man,prometheus,diia')).split(',')))
    keys = [key.strip() for key in keys if key.strip()]
    if not keys or any(key not in PROVIDERS for key in keys): raise ValueError('Choose man, prometheus, diia')
    return keys


async def sync_catalog(keys=None, limit=None, workers=2):
    keys = source_keys(','.join(keys) if isinstance(keys,list) else keys)
    limit = max(1,min(40,int(limit or os.getenv('CATALOG_SOURCE_LIMIT','12'))))
    results = await asyncio.to_thread(collect,keys,limit,workers)
    imported = 0
    for result in results:
        if result.events: imported += await db.upsert_events(result.events)
        async with db.Session() as session:
            state = await session.get(db.CatalogSource,result.key)
            if state is None:
                state = db.CatalogSource(key=result.key,name=result.name,url=result.url)
                session.add(state)
            state.last_attempt_at = db.utcnow()
            state.status = result.status
            state.fetched = len(result.events)
            state.error_code = result.error_code
            if result.events: state.last_success_at = state.last_attempt_at
            await session.commit()
    return {'imported':imported,'sources':[{'key':r.key,'status':r.status,'count':len(r.events)} for r in results],
            'ok':any(r.events for r in results)}
