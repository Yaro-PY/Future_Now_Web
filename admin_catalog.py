"""Admin operations: optimistic concurrency, audit trail and source-safe edits."""
from datetime import datetime
from sqlalchemy import select, update
from fastapi import Depends, Query
import database as db
import web_schemas as schema
from links import canonical_url, check_link
from catalog_status import stamp

EDIT_FIELDS = ('title','description','url','event_type','topics','country','city','format',
               'min_age','max_age','start_at','deadline','is_free','price_text','criteria',
               'organizer','participation_language','requirements','is_self_paced','is_closed')


def serial(value): return value.isoformat() if isinstance(value,datetime) else value


def published_out(row):
    values = {key:serial(getattr(row,key)) for key in EDIT_FIELDS}
    values['event_type'] = db.LEGACY_TYPES.get(row.event_type,row.event_type)
    values['is_free'] = row.is_free if row.price_known else None
    values['source'] = row.source
    return {'id':row.id,'revision':row.revision,'values':values,'status':db.event_status(row),
            'updated_at':stamp(row.updated_at),'admin_updated_at':stamp(row.admin_updated_at),
            'overridden_fields':sorted(row.admin_overrides or {})}


def report_out(row, event=None):
    return {'id':row.id,'event_id':row.event_id,'event_title':event.title if event else None,
            'category':row.category,'message':row.message,'status':row.status,
            'created_at':stamp(row.created_at),'updated_at':stamp(row.updated_at),'resolved_at':stamp(row.resolved_at),
            'review_note':row.review_note,'revision':row.revision}


def install(router, *, current_user, changing_user, require_admin, fail):
    @router.get('/admin/opportunities', tags=['Administration'])
    async def listings(q: str = Query('',max_length=120), state: str = Query('all',pattern='^(all|available|expired)$'),
                       page: int = Query(1,ge=1), page_size: int = Query(10,ge=1,le=50), user=Depends(current_user)):
        require_admin(user)
        async with db.Session() as session:
            stmt=select(db.Event).order_by(db.Event.updated_at.desc(),db.Event.id.desc())
            if q.strip(): stmt=stmt.where(db.Event.title.contains(q.strip(),autoescape=True))
            rows=list((await session.scalars(stmt)).all())
        if state!='all': rows=[row for row in rows if (db.event_status(row)=='expired')==(state=='expired')]
        return {'items':[published_out(row) for row in rows[(page-1)*page_size:page*page_size]],
                'total':len(rows),'page':page,'pages':max(1,(len(rows)+page_size-1)//page_size),'page_size':page_size}

    @router.get('/admin/opportunities/{event_id}', tags=['Administration'])
    async def listing(event_id: int, user=Depends(current_user)):
        require_admin(user)
        row=await db.get_event(event_id)
        if not row: fail('not_found',404)
        return published_out(row)

    @router.patch('/admin/opportunities/{event_id}', tags=['Administration'])
    async def edit(event_id: int, body: schema.PublishedEdit, user=Depends(changing_user)):
        require_admin(user)
        incoming=body.values.model_dump()
        incoming['url']=str(incoming['url'])
        async with db.distributed_lock('admin-catalog-edit') as acquired:
            if not acquired: fail('account_busy',409)
            async with db.Session() as session:
                row=await session.get(db.Event,event_id)
                if not row: fail('not_found',404)
                if row.revision!=body.expected_revision: fail('edit_conflict',409)
                if incoming['source']!=row.source: fail('invalid_request',422)
                if incoming['country']!='ukraine': incoming['city']=''
                values={key:incoming[key] for key in EDIT_FIELDS}
                values['price_known']=incoming['is_free'] is not None
                values['is_free']=incoming['is_free'] is True
                # Criteria are price facts, not a second independent price switch.
                if ('free' in values['criteria'] and not values['is_free']) or ('paid' in values['criteria'] and (values['is_free'] or not values['price_known'])):
                    fail('invalid_request',422)
                changes={key:{'before':serial(getattr(row,key)),'after':serial(value)}
                         for key,value in values.items() if getattr(row,key)!=value}
                if not changes: return published_out(row)
                if 'url' in changes:
                    urls=(await session.execute(select(db.Event.id,db.Event.url,db.Event.source_url).where(db.Event.id!=event_id))).all()
                    if any(canonical_url(values['url']) in {canonical_url(url),canonical_url(original) if original else ''} for _,url,original in urls):
                        fail('duplicate_url',409)
                    if not await check_link(values['url']): fail('link_unavailable',409)
                flags=dict(row.admin_overrides or {})
                protected=set(changes)
                for group in ({'is_free','price_known','price_text'}, {'min_age','max_age'}, {'country','city'}):
                    if protected & group: protected |= group
                flags.update({key:True for key in protected})
                now=db.utcnow()
                result=await session.execute(update(db.Event).where(db.Event.id==event_id,db.Event.revision==body.expected_revision)
                    .values(**values,source_url=row.source_url or row.url,admin_overrides=flags,revision=body.expected_revision+1,
                            updated_at=now,admin_updated_at=now,admin_updated_by=user.account.telegram_id))
                if result.rowcount!=1: fail('edit_conflict',409)
                session.add(db.AdminAudit(entity='event',entity_id=event_id,actor_id=user.account.telegram_id,changes=changes))
                await session.commit()
                await session.refresh(row)
                return published_out(row)

    @router.get('/admin/opportunities/{event_id}/history', tags=['Administration'])
    async def history(event_id: int, user=Depends(current_user)):
        require_admin(user)
        if not await db.get_event(event_id): fail('not_found',404)
        async with db.Session() as session:
            rows=(await session.scalars(select(db.AdminAudit).where(db.AdminAudit.entity=='event',db.AdminAudit.entity_id==event_id)
                                       .order_by(db.AdminAudit.id.desc()).limit(50))).all()
        return {'items':[{'id':row.id,'created_at':stamp(row.created_at),'changes':row.changes} for row in rows]}

    @router.get('/admin/reports', tags=['Administration'])
    async def reports(status: str = Query('all',pattern='^(all|open|new|in_progress|resolved|dismissed)$'),
                      page: int = Query(1,ge=1), page_size: int = Query(10,ge=1,le=50), user=Depends(current_user)):
        require_admin(user)
        async with db.Session() as session:
            stmt=select(db.Report,db.Event).outerjoin(db.Event,db.Report.event_id==db.Event.id).order_by(db.Report.id.desc())
            if status=='open': stmt=stmt.where(db.Report.status.in_(('new','in_progress')))
            elif status!='all': stmt=stmt.where(db.Report.status==status)
            rows=(await session.execute(stmt)).all()
        return {'items':[report_out(row,event) for row,event in rows[(page-1)*page_size:page*page_size]],
                'total':len(rows),'page':page,'pages':max(1,(len(rows)+page_size-1)//page_size),'page_size':page_size}

    @router.patch('/admin/reports/{report_id}', tags=['Administration'])
    async def review(report_id: int, body: schema.ReportReview, user=Depends(changing_user)):
        require_admin(user)
        async with db.Session() as session:
            row=await session.get(db.Report,report_id)
            if not row: fail('not_found',404)
            if row.revision!=body.expected_revision: fail('edit_conflict',409)
            if (row.status,row.review_note)==(body.status,body.review_note):
                return report_out(row,await session.get(db.Event,row.event_id) if row.event_id else None)
            changes={'status':{'before':row.status,'after':body.status},'review_note':{'before':row.review_note,'after':body.review_note}}
            now=db.utcnow()
            result=await session.execute(update(db.Report).where(db.Report.id==report_id,db.Report.revision==body.expected_revision)
                .values(status=body.status,review_note=body.review_note,reviewed_by=user.account.telegram_id,
                        updated_at=now,resolved_at=now if body.status in ('resolved','dismissed') else None,revision=body.expected_revision+1))
            if result.rowcount!=1: fail('edit_conflict',409)
            session.add(db.AdminAudit(entity='report',entity_id=report_id,actor_id=user.account.telegram_id,changes=changes))
            await session.commit()
            await session.refresh(row)
            return report_out(row,await session.get(db.Event,row.event_id) if row.event_id else None)
