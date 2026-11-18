"""Stable public listing URLs and HTML previews; no account data or schema changes."""
import re
import unicodedata
from html import escape

from fastapi import Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

import database as db
from event_media import cover_urls

_TRANSLITERATION=str.maketrans(dict(zip(
    'абвгґдеєжзиіїйклмнопрстуфхцчшщьюяыэъё',
    ['a','b','v','h','g','d','e','ye','zh','z','y','i','yi','y','k','l','m','n','o','p','r','s','t','u','f','kh','ts','ch','sh','shch','','yu','ya','y','e','','yo'])))


def opportunity_path(event):
    title=unicodedata.normalize('NFKC',event.title).casefold().translate(_TRANSLITERATION)
    slug=re.sub('[^a-z0-9]+','-',title).strip('-')[:90].rstrip('-') or 'opportunity'
    return f'/opportunities/{event.id}/{slug}'


def image_name(event):
    if event.event_type=='grant': return 'earthrise'
    if event.event_type in ('exchange','international','ukrainian','program'): return 'campus'
    if event.event_type in ('hackathon','internship') or 'it' in (event.topics or []): return 'technology'
    if event.event_type=='course': return ('technology','community','campus')[event.id%3]
    return 'community'


def install(app,static,headers):
    async def public_page(request: Request,event_id: int,slug: str=''):
        if not app.state.ready: return PlainTextResponse('Service temporarily unavailable',status_code=503,headers={'Cache-Control':'no-store'})
        frontend=static/'react/index.html'
        if not frontend.is_file(): return PlainTextResponse('Frontend unavailable',status_code=503)
        event=await db.get_event(event_id) if 0<event_id<=2147483647 else None
        html=frontend.read_text(encoding='utf-8')
        if not event:
            return HTMLResponse(html,status_code=404,headers={**headers,'X-Robots-Tag':'noindex'})
        path=opportunity_path(event)
        if request.url.path!=path:
            return RedirectResponse(path,status_code=308,headers={'Cache-Control':'no-cache'})
        origin=str(request.base_url).rstrip('/')
        canonical=origin+path
        title=escape(event.title+' — Future Now')
        description=escape(re.sub(r'\s+',' ',event.description or 'Освітні можливості у Future Now.').strip()[:220],quote=True)
        covers = await cover_urls([event_id])
        image_path = covers.get(event_id) or f'/assets/images/{image_name(event)}.jpg'
        image = escape(origin + image_path, quote=True)
        html=re.sub(r'<title>.*?</title>',lambda _:f'<title>{title}</title>',html,count=1,flags=re.S)
        html=re.sub(r'<meta name="description"[^>]*>',lambda _:f'<meta name="description" content="{description}">',html,count=1)
        meta=(f'<link rel="canonical" href="{escape(canonical,quote=True)}">'
              f'<meta property="og:type" content="website"><meta property="og:site_name" content="Future Now">'
              f'<meta property="og:title" content="{title}"><meta property="og:description" content="{description}">'
              f'<meta property="og:url" content="{escape(canonical,quote=True)}"><meta property="og:image" content="{image}">'
              '<meta name="twitter:card" content="summary_large_image">')
        html=html.replace('</head>',meta+'</head>',1)
        return HTMLResponse(html,headers=headers)

    app.add_api_route('/opportunities/{event_id:int}',public_page,methods=['GET'],include_in_schema=False)
    app.add_api_route('/opportunities/{event_id:int}/{slug:path}',public_page,methods=['GET'],include_in_schema=False)
