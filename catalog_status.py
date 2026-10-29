"""Read-only source health shared by the bot database and the website API."""
from datetime import timedelta
from sqlalchemy import select
import database as db


def stamp(value): return value.isoformat()+'Z' if value else None


async def catalog_status():
    async with db.Session() as session:
        rows = list((await session.scalars(select(db.CatalogSource).order_by(db.CatalogSource.key))).all())
    last = max((row.last_success_at for row in rows if row.last_success_at),default=None)
    stale = not rows or any(not row.last_success_at or row.last_success_at < db.utcnow()-timedelta(hours=48) for row in rows)
    return {'status':'never' if not rows else 'degraded' if stale or any(row.status!='ok' for row in rows) else 'ok',
            'last_checked_at':stamp(last),'stale':stale,'sources':[
                {'key':row.key,'name':row.name,'url':row.url,'status':row.status,'count':row.fetched,
                 'last_attempt_at':stamp(row.last_attempt_at),'last_success_at':stamp(row.last_success_at)} for row in rows]}
