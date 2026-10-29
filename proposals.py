"""Validation and conversion of user-authored suggestions before moderation."""
import ipaddress
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from pydantic import HttpUrl, TypeAdapter
from import_events import Opportunity
from database import localnow

FORM_FIELDS = ['title', 'url', 'description', 'type', 'topics', 'age', 'country',
               'city', 'format', 'deadline', 'criteria']
TEXT_FIELDS = {'title', 'url', 'description', 'deadline'}

def canonical_url(value):
    parsed = TypeAdapter(HttpUrl).validate_python(value)
    parts = urlsplit(str(parsed))
    host = (parts.hostname or '').lower()
    if parts.username or parts.password or '.' not in host or host.endswith(('.local', '.localhost', '.internal')) or host == 'localhost':
        raise ValueError('Not a public URL')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global: raise ValueError('Not a public URL')
    # Tracking and fragments must not let a repeated submission bypass deduplication.
    query = sorted((key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                   if not key.lower().startswith('utm_') and key.lower() not in ('fbclid', 'gclid'))
    result = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/') or '/', urlencode(query), ''))
    if len(result) > 2000: raise ValueError('URL too long')
    return result

def age_bounds(value):
    if value in ('any', None): return None, None
    if value == '18+': return 18, None
    low, high = map(int, str(value).replace('–', '-').split('-'))
    if not 0 <= low <= high <= 100: raise ValueError('Invalid age range')
    return low, high

def deadline_value(value):
    if not value: return None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            result = datetime.strptime(value, fmt)
            if result.date() < localnow().date(): raise ValueError('Expired deadline')
            return result
        except ValueError:
            continue
    raise ValueError('Invalid deadline')

def payload_from_draft(draft):
    low, high = age_bounds(draft.get('age'))
    criteria = draft.get('criteria', [])
    data = Opportunity(
        title=draft['title'].strip(), url=canonical_url(draft['url']),
        description=draft['description'].strip(), source='Пропозиція користувача / User suggestion',
        event_type=draft.get('type', 'other'), topics=draft.get('topics', []),
        min_age=low, max_age=high, country=draft.get('country', 'international'),
        city='' if draft.get('city', 'any') == 'any' else draft['city'],
        format=draft.get('format', 'unknown'), deadline=deadline_value(draft.get('deadline')),
        is_free=True if 'free' in criteria else False if 'paid' in criteria else None,
        criteria=criteria)
    return data.model_dump(mode='json')

def draft_from_payload(payload):
    low, high = payload.get('min_age'), payload.get('max_age')
    age = 'any' if low is None and high is None else '18+' if low == 18 and high is None else f'{low or 0}-{high or 100}'
    deadline = payload.get('deadline')
    return {'title': payload['title'], 'url': payload['url'], 'description': payload['description'],
            'type': payload['event_type'], 'topics': payload.get('topics', []), 'age': age,
            'country': payload.get('country', 'international'), 'city': payload.get('city') or 'any',
            'format': payload.get('format', 'unknown'), 'deadline': deadline[:10] if deadline else '',
            'criteria': payload.get('criteria', [])}
