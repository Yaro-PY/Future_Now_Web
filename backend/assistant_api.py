"""Authenticated, read-only assistant searches over the existing live catalogue."""
from fastapi import Depends
from pydantic import Field
from backend import database as db
from backend import web_schemas as schema
from backend.event_media import cover_urls
from backend.assistant_search import SearchContext, plan, rank, reply, describe, suggestions, choose

class AssistantRequest(schema.Input):
    message: str=Field(min_length=1,max_length=1000)
    context: SearchContext|None=None

def install(router,*,changing_user,effective_filters,event_out,event_flags,fail):
    @router.post('/assistant/message',tags=['Assistant'])
    async def message(body: AssistantRequest,user=Depends(changing_user)):
        if not body.message.strip(): fail('invalid_request',422)
        previous=body.context or SearchContext(filters=effective_filters(user.account),language=user.account.language)
        kind,context,extra=plan(body.message,previous)
        results=[];total=0
        if kind=='search':
            events=await db.search_events(context.filters.model_dump())
            scored=[(score,event) for event in events if (score:=rank(event,context)) is not None]
            scored.sort(key=lambda item:-item[0])
            total=len(scored)
            rows=[event for _,event in scored[(context.page-1)*3:context.page*3]]
            saved,subscribed=await event_flags(user.account.telegram_id)
            covers = await cover_urls([event.id for event in rows])
            results = [event_out(event, user.account.language, saved, subscribed, covers.get(event.id)) for event in rows]
        actions=[]
        if kind=='help': actions.append({'type':'navigate','route':extra['route']})
        if kind=='search' and not context.terms and context.age_min is None and context.level=='any' and not context.self_paced and not context.certificate:
            actions.append({'type':'catalog','filters':context.filters.model_dump()})
        return {'message':reply(kind,context,total,len(results),extra),'kind':kind,'context':context.model_dump(),
            'results':results,'total':total,'has_more':context.page*3<total,'page':context.page,
            'labels':describe(context),'suggestions':suggestions(context,kind,total),'actions':actions,
            'more_label':choose(context.language,'Показати ще','Показать ещё','Show more')}
